import os
import argparse
import logging
from urllib.parse import urlparse, urlunparse

import requests
import bs4
from markdownify import MarkdownConverter
from atlassian import Confluence

ATTACHMENT_FOLDER_NAME = "attachments"
DOWNLOAD_CHUNK_SIZE = 4 * 1024 * 1024  # 4MB

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class ExportException(Exception):
    pass


class Exporter:
    def __init__(self, url, username, token, out_dir, space, no_attach, removable_parents):
        self.__out_dir = out_dir
        self.__parsed_url = urlparse(url)
        self.__username = username
        self.__token = token
        self.__confluence = Confluence(url=urlunparse(self.__parsed_url),
                                       username=self.__username,
                                       password=self.__token)
        self.__seen = set()
        self.__no_attach = no_attach
        self.__space = space
        self.__removable_parents = removable_parents

        # Ensure the output directory exists
        os.makedirs(self.__out_dir, exist_ok=True)

    @staticmethod
    def __sanitize_filename(document_name_raw):
        """
        Sanitize the document name to make it safe for use as a filename.
        """
        document_name = document_name_raw
        for invalid in ["..", "/"]:
            if invalid in document_name:
                logging.warning("Dangerous page title: \"%s\", \"%s\" found, replacing it with \"_\"",
                                document_name, invalid)
                document_name = document_name.replace(invalid, "_")
        return document_name

    def __dump_page(self, src_id, parents):
        """
        Dump a single Confluence page to the output directory, including its attachments.
        Recursively process any child pages.
        """
        if src_id in self.__seen:
            raise ExportException("Duplicate Page ID Found!")

        page = self.__confluence.get_page_by_id(src_id, expand="body.storage,version")
        page_title = page["title"]
        page_id = page["id"]

        child_ids = self.__confluence.get_child_id_list(page_id)
        content = page["body"]["storage"]["value"]
        last_updated = page["version"]["when"]

        # Add last updated timestamp to the content
        content += f'<div>Last updated: {last_updated}</div>'

        extension = ".html"
        document_name = "index" if child_ids else page_title

        sanitized_filename = self.__sanitize_filename(document_name) + extension
        sanitized_parents = list(map(self.__sanitize_filename, parents))

        # Skip adding specified removable parents to the path
        sanitized_parents = [p for p in sanitized_parents if p not in self.__removable_parents]

        page_location = sanitized_parents + [sanitized_filename]
        page_filename = os.path.join(self.__out_dir, *page_location)

        # Ensure the directory for the page exists
        os.makedirs(os.path.dirname(page_filename), exist_ok=True)
        logging.info("Saving to %s", " / ".join(page_location))

        # Save the page content to an HTML file
        with open(page_filename, "w", encoding="utf-8") as f:
            f.write(content)

        # Fetch and save attachments if not disabled
        if not self.__no_attach:
            self.__fetch_attachments(page_id, page_filename)

        self.__seen.add(page_id)

        # Recursively process child pages
        for child_id in child_ids:
            self.__dump_page(child_id, parents=sanitized_parents + [page_title])

    def __fetch_attachments(self, page_id, page_filename):
        """
        Fetch and save attachments for a given page.
        Only image attachments are saved locally; others are linked to their Atlassian URLs.
        """
        ret = self.__confluence.get_attachments_from_content(page_id, start=0, limit=500)
        page_dir = os.path.dirname(page_filename)
        for attachment in ret["results"]:
            att_title = attachment["title"]
            download = attachment["_links"]["download"]
            att_url = urlunparse(
                (self.__parsed_url.scheme, self.__parsed_url.netloc, "/wiki/" + download.lstrip("/"), None, None, None)
            )

            att_sanitized_name = self.__sanitize_filename(att_title)
            att_filename = os.path.join(page_dir, ATTACHMENT_FOLDER_NAME, att_sanitized_name)
            os.makedirs(os.path.dirname(att_filename), exist_ok=True)

            mime_type = attachment["metadata"]["mediaType"]
            if mime_type.startswith("image/"):
                logging.info("Checking for existing image attachment %s", att_filename)
                if os.path.exists(att_filename):
                    logging.info("Attachment %s already exists. Skipping download.", att_filename)
                else:
                    logging.info("Saving image attachment %s to %s", att_title, att_filename)
                    self.__download_attachment(att_url, att_filename)
            else:
                logging.info("Adding link to non-image attachment %s", att_title)
                self.__add_attachment_link(page_filename, att_title, att_url)

    def __download_attachment(self, att_url, att_filename):
        """
        Download an attachment from Confluence and save it locally.
        """
        try:
            with requests.get(att_url, auth=(self.__username, self.__token), stream=True) as r:
                r.raise_for_status()
                with open(att_filename, "wb") as f:
                    for buf in r.iter_content(chunk_size=DOWNLOAD_CHUNK_SIZE):
                        f.write(buf)
        except requests.RequestException as e:
            logging.error("Error downloading attachment %s: %s", att_url, e)

    def __add_attachment_link(self, page_filename, att_title, att_url):
        """
        Add a link to a non-image attachment in the HTML content of a page.
        """
        with open(page_filename, "r+", encoding="utf-8") as f:
            content = f.read()
            soup = bs4.BeautifulSoup(content, 'html.parser')
            body = soup.body
            if body is None:
                body = soup.new_tag("body")
                soup.append(body)
            link_tag = soup.new_tag("a", href=att_url)
            link_tag.string = att_title
            body.append(link_tag)
            f.seek(0)
            f.write(str(soup))
            f.truncate()

    def __dump_space(self, space):
        """
        Dump all pages and attachments in a Confluence space.
        """
        space_key = space["key"]
        logging.info("Processing space %s", space_key)
        homepage = space.get("homepage")
        if homepage is None:
            logging.error("Skipping space: %s, no homepage found!", space_key)
            raise ExportException("No homepage found")
        else:
            homepage_id = homepage["id"]
            self.__dump_page(homepage_id, parents=[])

    def dump(self):
        """
        Dump all spaces in Confluence or a specific space if specified.
        """
        ret = self.__confluence.get_all_spaces(start=0, limit=500, expand='description.plain,homepage')
        if ret['size'] == 0:
            logging.error("No spaces found in confluence. Please check credentials")
            return

        for space in ret["results"]:
            if self.__space is None or space["key"] == self.__space:
                self.__dump_space(space)


class Converter:
    def __init__(self, out_dir, remove_html):
        self.__out_dir = out_dir
        self.__remove_html = remove_html

    def recurse_findfiles(self, path):
        """
        Recursively find all files in a given directory.
        """
        for entry in os.scandir(path):
            if entry.is_dir(follow_symlinks=False):
                yield from self.recurse_findfiles(entry.path)
            elif entry.is_file(follow_symlinks=False):
                yield entry
            else:
                raise NotImplementedError()

    def __convert_atlassian_html(self, soup):
        """
        Convert Atlassian-specific HTML tags to standard HTML tags and
        convert video links to Markdown format with ![type:video](url).
        """
        for image in soup.find_all("ac:image"):
            url = None
            for child in image.children:
                url = child.get("ri:filename", None)
                break

            if url is None:
                continue

            srcurl = os.path.join(ATTACHMENT_FOLDER_NAME, url)
            imgtag = soup.new_tag("img", attrs={"src": srcurl, "alt": srcurl})

            image.insert_after(soup.new_tag("br"))
            image.replace_with(imgtag)

        for attachment in soup.find_all("ac:link"):
            if attachment.get("ac:link-type") == "attachment":
                att_filename = attachment.get("ri:filename")
                attachment_tag = soup.new_tag("a", href=os.path.join(ATTACHMENT_FOLDER_NAME, att_filename))
                attachment_tag.string = att_filename
                attachment.replace_with(attachment_tag)

        # Convert video links
        for link in soup.find_all("a"):
            href = link.get("href", "")
            if any(href.endswith(ext) for ext in [".mp4", ".avi", ".mkv", ".mov", ".flv", ".wmv", ".m4v", ".webm"]):
                video_md = f'![type:video]({href})'
                new_tag = soup.new_string(video_md)
                link.replace_with(new_tag)

        return soup

    def convert(self):
        """
        Convert all HTML files in the output directory to Markdown.
        Optionally remove the original HTML files after conversion.
        """
        for entry in self.recurse_findfiles(self.__out_dir):
            path = entry.path

            if not path.endswith(".html"):
                continue

            logging.info("Converting %s", path)
            with open(path, "r", encoding="utf-8") as f:
                data = f.read()

            soup_raw = bs4.BeautifulSoup(data, 'html.parser')
            soup = self.__convert_atlassian_html(soup_raw)

            md = MarkdownConverter().convert_soup(soup)
            newname = os.path.splitext(path)[0]
            with open(newname + ".md", "w", encoding="utf-8") as f:
                f.write(md)

            if self.__remove_html:
                os.remove(path)
                logging.info("Removed HTML file %s", path)


if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("url", type=str, help="The url to the confluence instance")
    parser.add_argument("username", type=str, help="The username")
    parser.add_argument("token", type=str, help="The access token to Confluence")
    parser.add_argument("out_dir", type=str, help="The directory to output the files to")
    parser.add_argument("--space", type=str, required=False, default=None, help="Spaces to export")
    parser.add_argument("--skip-attachments", action="store_true", dest="no_attach", required=False,
                        default=False, help="Skip fetching attachments")
    parser.add_argument("--no-fetch", action="store_true", dest="no_fetch", required=False,
                        default=False, help="This option only runs the markdown conversion")
    parser.add_argument("--remove-html", action="store_true", dest="remove_html", required=False,
                        default=False, help="Remove HTML files after conversion")
    parser.add_argument("--removable-parents", type=str, nargs="*", default=[],
                        help="List of parent titles to be removed from the path")

    args = parser.parse_args()

    if not args.no_fetch:
        # Export pages and attachments from Confluence
        dumper = Exporter(url=args.url, username=args.username, token=args.token, out_dir=args.out_dir,
                          space=args.space, no_attach=args.no_attach, removable_parents=args.removable_parents)
        dumper.dump()

    # Convert HTML files to Markdown
    converter = Converter(out_dir=args.out_dir, remove_html=args.remove_html)
    converter.convert()
