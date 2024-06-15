# Confluence to Markdown Converter

This project provides a tool to export Confluence pages (including attachments) to a local directory and convert the pages from HTML to Markdown format. It allows for selective removal of specified parent directories from the path structure.

## Features

- **Export Confluence Pages:** Export pages from a specific space or all spaces.
- **Directory and File Handling:** Automatically creates the output directory, sanitizes filenames, and allows removal of specified parent directories from the path.
- **Attachment Handling:** Downloads image attachments, skips already existing attachments, and links non-image attachments to their original location.
- **HTML to Markdown Conversion:** Converts exported HTML pages to Markdown format.
- **Special Content Handling:**
  - Appends the last updated timestamp of each page to the bottom.
  - Converts video file links to the format `![type:video](url)`.
- **Command-Line Interface:** Customizable behavior with various arguments.
- **Detailed Logging:** Provides detailed logging throughout the process.

## Requirements

- Python 3.x
- The following Python packages:
  - `requests`
  - `beautifulsoup4`
  - `markdownify`
  - `atlassian-python-api`

You can install the required packages using `pip`:

```sh
pip install requests beautifulsoup4 markdownify atlassian-python-api
```

## Usage

```sh
python3 main.py <url> <username> <token> <out_dir> [--space <space>] [--skip-attachments] [--no-fetch] [--remove-html] [--removable-parents <parents>...]
```

### Arguments

- `<url>`: The URL to the Confluence instance.
- `<username>`: The username for Confluence authentication.
- `<token>`: The access token for Confluence authentication.
- `<out_dir>`: The directory to output the files to.

### Optional Arguments

- `--space <space>`: The space key to export. If not specified, all spaces will be exported.
- `--skip-attachments`: Skip fetching attachments.
- `--no-fetch`: Only run the Markdown conversion, skipping the export step.
- `--remove-html`: Remove HTML files after conversion.
- `--removable-parents <parents>...`: A list of parent titles to be removed from the path. Multiple parents can be specified separated by spaces.

### Examples

#### Export a specific space and convert to Markdown

```sh
python3 main.py https://your-confluence-instance.atlassian.net username token docs --space YOURSPACE --remove-html
```

#### Export all spaces and skip attachments

```sh
python3 main.py https://your-confluence-instance.atlassian.net username token docs --skip-attachments
```

#### Export and remove specific parent directories from the path

```sh
python3 main.py https://your-confluence-instance.atlassian.net username token docs --space YOURSPACE --removable-parents "Welcome!" "Another Parent"
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
