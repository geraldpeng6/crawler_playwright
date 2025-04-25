# Web Interaction Element Crawler

A tool for automatically crawling and detecting interactive elements (such as like buttons, vote buttons, etc.) on web pages. It supports both GUI and command-line interfaces, and can save browser profiles to handle websites that require login.

## Features

- 🔍 Automatically identify interactive elements (like buttons, vote buttons, comment buttons, etc.)
- 🖱️ Simulate clicks on interactive elements and record results
- 📊 Save crawling results in JSON format and webpage screenshots
- 🔐 Support for saving browser profiles (including cookies and login status)
- 📋 Support for batch importing URLs from CSV files
- 🎛️ Provides both graphical user interface (GUI) and command-line interface
- 🔧 Highly customizable parameters

## System Requirements

- Python 3.8+
- Chrome browser

## Installation Guide

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/crawler_playwright.git
cd crawler_playwright
```

### 2. Set up the environment

Using the setup scripts (recommended):

**On macOS/Linux:**
```bash
chmod +x setup.sh
./setup.sh
```

**On Windows:**
```bash
setup.bat
```

Or manually:

```bash
# Install uv
pip install uv

# Create virtual environment
uv venv

# Activate virtual environment
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate  # Windows

# Install dependencies
uv pip install -r requirements.txt

# Install Playwright browsers
python -m playwright install chromium
```

## Usage

### GUI Mode

Start the GUI interface:

```bash
python run_gui.py
```

The GUI interface provides the following features:
- Select CSV file (containing URLs to crawl)
- Set output directory
- Adjust crawler parameters (similarity threshold, scroll count, delay time, etc.)
- Add custom keywords
- Create and manage browser profiles
- Real-time log display

### Command-line Mode

```bash
python main.py path/to/urls.csv [--headless] [--output-dir OUTPUT_DIR] [--profile PROFILE] [options]
```

Basic Parameters:
- `path/to/urls.csv`: Path to CSV file containing URLs
- `--headless`: Run browser in headless mode (no visible window)
- `--output-dir`: Specify output directory, default is "output"
- `--profile`: Browser profile to use

Crawler Settings:
- `--similarity`: Similarity threshold for keyword matching (0-100, default: 70)
- `--scroll-count`: Number of times to scroll the page (default: 3)
- `--delay`: Delay between URLs in seconds (default: 2.0)

Anti-Crawler Settings:
- `--random-delay`: Use random delay between requests
- `--min-delay`: Minimum delay in seconds (default: 1.0)
- `--max-delay`: Maximum delay in seconds (default: 5.0)
- `--rotate-user-agent`: Rotate user agents for each request
- `--use-referrers`: Add HTTP referrer headers
- `--rate-limit`: Enable rate limiting
- `--requests-per-minute`: Maximum requests per minute (default: 20)
- `--retry-count`: Number of retry attempts on failure (default: 3)
- `--retry-backoff`: Exponential backoff factor for retries (default: 2.0)
- `--emulate-human`: Emulate human-like behavior

Multi-Threading Settings:
- `--multithreading`: Enable multi-threaded crawling for different domains
- `--threads`: Maximum number of threads to use (default: 4)
- `--domains-per-thread`: Maximum number of domains per thread (default: 2)

## Browser Profiles

### Creating a Browser Profile

1. In the GUI interface, click the "Manage Profiles" button
2. Enter a profile name
3. Click the "Open Browser" button
4. Log in or set the required cookies in the opened browser
5. When finished, close the browser and click "OK"

### Using a Browser Profile

1. In the GUI interface, select the created profile from the dropdown menu
2. Start the crawler normally, it will use the cookies and login status from the selected profile

## CSV File Format

The CSV file should contain a list of URLs. The program will automatically identify the column containing URLs. Example:

```csv
url,name,category
https://example.com/page1,Example 1,News
https://example.com/page2,Example 2,Blog
```

## Output Format

The crawler generates two files for each processed URL:

1. JSON file: Contains detailed information about the found interactive elements
   ```json
   {
     "url": "https://example.com/page1",
     "timestamp": "20230101_120000",
     "elements_count": 2,
     "elements": [
       {
         "element_text": "Like",
         "element_tag": "button",
         "element_class": "like-button",
         "element_id": "like-btn",
         "element_xpath": "//button[@class='like-button']",
         "match_type": "keyword_match",
         "match_keyword": "like"
       },
       ...
     ]
   }
   ```

2. PNG file: Screenshot of the webpage, showing the found interactive elements

## Custom Keywords

You can add custom keywords in the GUI interface, one per line. These keywords will be used to identify interactive elements.

Default keywords include:
- like
- vote
- upvote
- downvote
- favorite
- follow
- subscribe
- share
- comment
- reply
- etc.

## Advanced Configuration

### Crawler Settings

#### Similarity Threshold

Controls the flexibility of keyword matching (0-100). Lower values will match more elements but may include false positives; higher values match more precisely but may miss some elements.

#### Scroll Count

Controls the number of times the page is scrolled, used to load lazy-loaded elements.

#### Delay Time

Wait time between URLs (in seconds), to avoid being detected as a crawler by websites.

### Anti-Crawler Features

The crawler includes several anti-detection mechanisms to help avoid being blocked by websites:

#### Random Delays

Instead of using a fixed delay between requests, the crawler can use random delays within a specified range. This makes the request pattern less predictable and more human-like.

#### User Agent Rotation

The crawler can rotate through different user agent strings for each request, making it harder for websites to identify it as a bot based on a consistent user agent.

#### HTTP Referrer Spoofing

Adds realistic HTTP referrer headers to requests, making them appear to come from search engines or other legitimate sources.

#### Rate Limiting

Limits the number of requests per minute to avoid triggering rate-limiting mechanisms on websites.

#### Retry Mechanism

Automatically retries failed requests with exponential backoff, helping to handle temporary network issues or server-side rate limiting.

#### Human Behavior Emulation

Simulates human-like behavior such as random scrolling, mouse movements, and variable timing between actions.

### Multi-Threading Features

The crawler supports multi-threaded operation to improve performance when crawling multiple different websites:

#### Domain-Based Threading

Crawls different domains in parallel while maintaining per-domain rate limits. This allows you to crawl multiple websites simultaneously without triggering anti-crawler protections.

#### Configurable Thread Pool

Customize the number of threads and domains per thread to optimize performance for your specific hardware and network conditions.

#### Thread Safety

All operations are thread-safe, ensuring that data is properly synchronized between threads.

## Troubleshooting

### Browser Driver Issues

The program will automatically download the WebDriver suitable for your Chrome version. If you encounter problems, make sure your Chrome browser is up to date.

### Unable to Identify Elements

If the crawler cannot identify certain interactive elements:
1. Try lowering the similarity threshold
2. Add custom keywords
3. Check if the elements use uncommon HTML structures

### Being Blocked by Websites

If you encounter being blocked by websites:
1. Enable anti-crawler features in the Settings tab of the GUI or use the corresponding command-line options
2. Increase the delay time or use random delays with higher minimum/maximum values
3. Enable user agent rotation and HTTP referrer spoofing
4. Use browser profiles to maintain cookies and login state
5. Enable rate limiting with a lower requests-per-minute value
6. Enable human behavior emulation
7. Avoid crawling a large number of pages from the same website in a short time
8. Consider using proxy servers for high-volume crawling (available in the Advanced settings tab)

### Performance Optimization

To optimize crawling performance:
1. Enable multi-threading when crawling multiple different domains
2. Adjust the number of threads based on your CPU cores (typically 1-2 threads per core)
3. Set an appropriate domains-per-thread value (2-3 is usually optimal)
4. Use headless mode for faster operation when visual feedback isn't needed
5. Balance speed with anti-detection measures - faster isn't always better

## License

[MIT License](LICENSE)

## Contributing

Contributions, bug reports, and pull requests are welcome!
