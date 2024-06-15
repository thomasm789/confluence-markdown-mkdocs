# Confluence to Markdown Converter

This project provides a tool to export Confluence pages (including attachments) to a local directory and convert the pages from HTML to Markdown format. It allows for selective removal of specified parent directories from the path structure.

## Features

- Export Confluence pages and their attachments.
- Convert exported HTML pages to Markdown format.
- Optionally remove HTML files after conversion.
- Skip specified parent directories in the path structure.

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
