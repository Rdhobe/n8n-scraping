
from flask import Flask, request, jsonify
from selenium import webdriver 
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import re
from urllib.parse import quote_plus

app = Flask(__name__)

class SocialMediaScraper:
    def __init__(self, twitter_username=None, twitter_password=None):
        self.twitter_username = twitter_username
        self.twitter_password = twitter_password
        
        self.chrome_options = Options()
        # Remove headless mode for debugging - you can add it back later
        self.chrome_options.add_argument('--headless')
        self.chrome_options.add_argument('--no-sandbox')
        self.chrome_options.add_argument('--disable-dev-shm-usage')
        self.chrome_options.add_argument('--start-maximized')
        self.chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        self.chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.chrome_options.add_experimental_option('useAutomationExtension', False)
        self.chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        # Add these options for better YouTube compatibility
        self.chrome_options.add_argument('--disable-web-security')
        self.chrome_options.add_argument('--allow-running-insecure-content')
        self.chrome_options.add_argument('--disable-features=VizDisplayCompositor')
        self.service = Service(ChromeDriverManager().install())

    def twitter_login(self, driver):
        try:
            driver.get('https://twitter.com/login')
            time.sleep(3)
            username_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[autocomplete="username"]'))
            )
            username_field.send_keys(self.twitter_username)
            username_field.send_keys(Keys.RETURN)
            time.sleep(2)
            password_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[name="password"]'))
            )
            password_field.send_keys(self.twitter_password)
            password_field.send_keys(Keys.RETURN)
            time.sleep(5)
            return True
        except Exception as e:
            print(f"Twitter login error: {str(e)}")
            return False

    def extract_twitter_engagement_metrics(self, tweet_element):
        """Extract likes, retweets, replies, and views from tweet element"""
        metrics = {
            'likes': '0',
            'retweets': '0', 
            'replies': '0',
            'views': '0'
        }
        
        try:
            # Method 1: Try to get metrics from aria-label attributes
            engagement_buttons = tweet_element.find_elements(By.CSS_SELECTOR, 'div[role="group"] > div')
            
            for button in engagement_buttons:
                try:
                    aria_label = button.get_attribute('aria-label')
                    if aria_label:
                        # Extract numbers from aria-label
                        numbers = re.findall(r'[\d,]+', aria_label)
                        if numbers:
                            count = numbers[0].replace(',', '')
                            
                            if 'reply' in aria_label.lower() or 'replies' in aria_label.lower():
                                metrics['replies'] = count
                            elif 'repost' in aria_label.lower() or 'retweet' in aria_label.lower():
                                metrics['retweets'] = count
                            elif 'like' in aria_label.lower():
                                metrics['likes'] = count
                            elif 'view' in aria_label.lower():
                                metrics['views'] = count
                except:
                    continue
            
            # Method 2: Try alternative selectors for engagement metrics
            if metrics['likes'] == '0':
                like_elements = tweet_element.find_elements(By.CSS_SELECTOR, 'button[data-testid="like"] span, div[data-testid="like"] span')
                for elem in like_elements:
                    text = elem.text.strip()
                    if text and text.isdigit():
                        metrics['likes'] = text
                        break
            
            if metrics['retweets'] == '0':
                retweet_elements = tweet_element.find_elements(By.CSS_SELECTOR, 'button[data-testid="retweet"] span, div[data-testid="retweet"] span')
                for elem in retweet_elements:
                    text = elem.text.strip()
                    if text and (text.isdigit() or 'K' in text or 'M' in text):
                        metrics['retweets'] = text
                        break
            
            if metrics['replies'] == '0':
                reply_elements = tweet_element.find_elements(By.CSS_SELECTOR, 'button[data-testid="reply"] span, div[data-testid="reply"] span')
                for elem in reply_elements:
                    text = elem.text.strip()
                    if text and (text.isdigit() or 'K' in text or 'M' in text):
                        metrics['replies'] = text
                        break
                        
        except Exception as e:
            print(f"Error extracting Twitter engagement metrics: {str(e)}")
        
        return metrics

    def scrape_tweets(self, search_term, num_tweets=50):
        tweets = []
        try:
            driver = webdriver.Chrome(service=self.service, options=self.chrome_options)
            
            # Add stealth settings
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            if not self.twitter_login(driver):
                driver.quit()
                return {"error": "Twitter login failed"}

            driver.get(f"https://x.com/search?q={search_term}&src=typed_query&f=live")
            time.sleep(5)
            
            last_height = driver.execute_script("return document.body.scrollHeight")
            scroll_attempts = 0
            max_scroll_attempts = 20

            while len(tweets) < num_tweets and scroll_attempts < max_scroll_attempts:
                try:
                    tweet_elements = WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'article[data-testid="tweet"]'))
                    )

                    for tweet in tweet_elements:
                        if len(tweets) >= num_tweets:
                            break
                        try:
                            # Extract tweet text
                            text_element = tweet.find_element(By.CSS_SELECTOR, '[data-testid="tweetText"]')
                            text = text_element.text if text_element else ""
                            
                            # Extract timestamp
                            time_element = tweet.find_element(By.TAG_NAME, 'time')
                            time_tag = time_element.get_attribute('datetime') if time_element else ""
                            
                            # Extract username
                            username_element = tweet.find_element(By.CSS_SELECTOR, '[data-testid="User-Name"] a')
                            username = username_element.get_attribute('href').split('/')[-1] if username_element else ""

                            # Extract engagement metrics using improved method
                            engagement_metrics = self.extract_twitter_engagement_metrics(tweet)

                            tweet_data = {
                                'platform': 'twitter',
                                'text': text,
                                'time': time_tag,
                                'username': username,
                                'likes': engagement_metrics['likes'],
                                'retweets': engagement_metrics['retweets'],  
                                'replies': engagement_metrics['replies'],
                                'views': engagement_metrics['views']
                            }

                            # Check if this tweet is already in our list (avoid duplicates)
                            tweet_exists = any(
                                existing_tweet['text'] == tweet_data['text'] and 
                                existing_tweet['username'] == tweet_data['username'] 
                                for existing_tweet in tweets
                            )
                            
                            if not tweet_exists and tweet_data['text']:
                                tweets.append(tweet_data)
                                print(f"Scraped tweet {len(tweets)}: {tweet_data['username']} - Likes: {tweet_data['likes']}, RTs: {tweet_data['retweets']}")
                                
                        except Exception as e:
                            print(f"Error processing individual tweet: {str(e)}")
                            continue

                    # Scroll down to load more tweets
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(3)
                    
                    new_height = driver.execute_script("return document.body.scrollHeight")
                    if new_height == last_height:
                        scroll_attempts += 1
                        time.sleep(2)
                    else:
                        scroll_attempts = 0
                        
                    last_height = new_height
                    
                except Exception as e:
                    print(f"Error in Twitter scroll iteration: {str(e)}")
                    scroll_attempts += 1
                    time.sleep(2)

            driver.quit()
            return tweets
            
        except Exception as e:
            if 'driver' in locals():
                driver.quit()
            return {"error": str(e)}

    def extract_youtube_video_data(self, video_element):
        """Extract video data from YouTube video element"""
        video_data = {
            'platform': 'youtube',
            'title': '',
            'channel': '',
            'views': '0',
            'upload_time': '',
            'duration': '',
            'thumbnail': '',
            'video_url': '',
            'description': ''
        }
        
        try:
            # Multiple methods to extract title and URL
            title_element = None
            title_selectors = [
                'a#video-title',
                'h3 a',
                'h3.ytd-video-renderer a',
                '.ytd-video-renderer h3 a',
                'a[href*="/watch?v="]'
            ]
            
            for selector in title_selectors:
                try:
                    title_element = video_element.find_element(By.CSS_SELECTOR, selector)
                    if title_element and title_element.text.strip():
                        video_data['title'] = title_element.text.strip()
                        video_data['video_url'] = title_element.get_attribute('href')
                        break
                except:
                    continue
            
            # Extract channel name with multiple selectors
            channel_selectors = [
                'a.yt-simple-endpoint.style-scope.yt-formatted-string',
                '.ytd-channel-name a',
                '#channel-name a',
                '.ytd-video-owner-renderer a',
                'a[href*="/channel/"]',
                'a[href*="/@"]'
            ]
            
            for selector in channel_selectors:
                try:
                    channel_elem = video_element.find_element(By.CSS_SELECTOR, selector)
                    if channel_elem and channel_elem.text.strip():
                        video_data['channel'] = channel_elem.text.strip()
                        break
                except:
                    continue
            
            # Extract metadata (views and upload time)
            metadata_selectors = [
                'span.style-scope.ytd-video-meta-block',
                '#metadata-line span',
                '.ytd-video-meta-block span'
            ]
            
            for selector in metadata_selectors:
                try:
                    metadata_elements = video_element.find_elements(By.CSS_SELECTOR, selector)
                    for elem in metadata_elements:
                        text = elem.text.strip()
                        if text:
                            if 'view' in text.lower():
                                video_data['views'] = text
                            elif any(word in text.lower() for word in ['ago', 'day', 'week', 'month', 'year', 'hour', 'minute']):
                                video_data['upload_time'] = text
                    if video_data['views'] != '0' and video_data['upload_time']:
                        break
                except:
                    continue
            
            # Extract duration with multiple selectors
            duration_selectors = [
                'span.ytd-thumbnail-overlay-time-status-renderer',
                '.badge-shape-wiz__text',
                'span.style-scope.ytd-thumbnail-overlay-time-status-renderer'
            ]
            
            for selector in duration_selectors:
                try:
                    duration_elem = video_element.find_element(By.CSS_SELECTOR, selector)
                    if duration_elem and duration_elem.text.strip():
                        video_data['duration'] = duration_elem.text.strip()
                        break
                except:
                    continue
            
            # Extract thumbnail
            try:
                img_elements = video_element.find_elements(By.TAG_NAME, 'img')
                for img in img_elements:
                    src = img.get_attribute('src')
                    if src and ('ytimg.com' in src or 'ggpht.com' in src):
                        video_data['thumbnail'] = src
                        break
            except:
                pass
                    
        except Exception as e:
            print(f"Error extracting YouTube video data: {str(e)}")
        
        return video_data

    def scrape_youtube_videos(self, search_term, num_videos=50):
        videos = []
        try:
            driver = webdriver.Chrome(service=self.service, options=self.chrome_options)
            
            # Add stealth settings
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Navigate to YouTube search
            encoded_search = quote_plus(search_term)
            driver.get(f"https://www.youtube.com/results?search_query={encoded_search}")
            
            # Wait longer for initial page load
            time.sleep(8)
            
            # Wait for the page to fully load
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'ytd-video-renderer'))
                )
            except:
                print("Initial video elements not found, trying alternative approach...")
                # Try scrolling to trigger content loading
                driver.execute_script("window.scrollTo(0, 500);")
                time.sleep(3)
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(3)
            
            last_height = driver.execute_script("return document.body.scrollHeight")
            scroll_attempts = 0
            max_scroll_attempts = 15
            
            print(f"Starting YouTube scraping for: {search_term}")

            while len(videos) < num_videos and scroll_attempts < max_scroll_attempts:
                try:
                    # Multiple selectors to find video containers
                    video_selectors = [
                        'ytd-video-renderer',
                        'ytd-compact-video-renderer',
                        'div.ytd-video-renderer',
                        '[class*="video-renderer"]'
                    ]
                    
                    video_elements = []
                    for selector in video_selectors:
                        try:
                            elements = driver.find_elements(By.CSS_SELECTOR, selector)
                            if elements:
                                video_elements = elements
                                print(f"Found {len(video_elements)} video elements using selector: {selector}")
                                break
                        except:
                            continue
                    
                    if not video_elements:
                        print("No video elements found, scrolling to load more content...")
                        scroll_attempts += 1
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(4)
                        continue
                    
                    print(f"Processing {len(video_elements)} video elements...")
                    
                    for i, video_elem in enumerate(video_elements):
                        if len(videos) >= num_videos:
                            break
                            
                        try:
                            # Scroll element into view
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", video_elem)
                            time.sleep(0.5)
                            
                            video_data = self.extract_youtube_video_data(video_elem)
                            
                            # Debug output
                            print(f"Video {i+1} - Title: '{video_data['title'][:30]}...', Channel: '{video_data['channel']}'")
                            
                            # Only add if we have meaningful data
                            if video_data['title'] and len(video_data['title']) > 3:
                                # Check for duplicates
                                video_exists = any(
                                    existing_video['title'] == video_data['title']
                                    for existing_video in videos
                                )
                                
                                if not video_exists:
                                    videos.append(video_data)
                                    print(f"✓ Scraped video {len(videos)}: {video_data['title'][:50]}... - {video_data['channel']}")
                                else:
                                    print(f"✗ Duplicate video skipped: {video_data['title'][:30]}...")
                            else:
                                print(f"✗ Incomplete data for video {i+1}")
                                    
                        except Exception as e:
                            print(f"Error processing video {i+1}: {str(e)}")
                            continue
                    
                    # Scroll down to load more videos
                    print("Scrolling to load more videos...")
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(4)
                    
                    new_height = driver.execute_script("return document.body.scrollHeight")
                    if new_height == last_height:
                        scroll_attempts += 1
                        print(f"No new content loaded. Scroll attempt {scroll_attempts}/{max_scroll_attempts}")
                        time.sleep(3)
                    else:
                        scroll_attempts = 0
                        print(f"New content loaded. Total videos so far: {len(videos)}")
                        
                    last_height = new_height
                    
                except Exception as e:
                    print(f"Error in YouTube scroll iteration: {str(e)}")
                    scroll_attempts += 1
                    time.sleep(3)

            print(f"YouTube scraping completed. Total videos: {len(videos)}")
            driver.quit()
            return videos
            
        except Exception as e:
            print(f"Critical YouTube scraping error: {str(e)}")
            if 'driver' in locals():
                driver.quit()
            return {"error": str(e)}

    def scrape_youtube_comments(self, video_url, num_comments=50):
        """Scrape comments from a specific YouTube video"""
        comments = []
        try:
            driver = webdriver.Chrome(service=self.service, options=self.chrome_options)
            
            # Add stealth settings
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            driver.get(video_url)
            time.sleep(5)
            
            # Scroll down to load comments section
            driver.execute_script("window.scrollTo(0, 1000);")
            time.sleep(3)
            
            last_height = driver.execute_script("return document.body.scrollHeight")
            scroll_attempts = 0
            max_scroll_attempts = 15

            while len(comments) < num_comments and scroll_attempts < max_scroll_attempts:
                try:
                    # Wait for comments to load
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'ytd-comment-thread-renderer'))
                    )
                    
                    comment_elements = driver.find_elements(By.CSS_SELECTOR, 'ytd-comment-thread-renderer')
                    
                    for comment_elem in comment_elements:
                        if len(comments) >= num_comments:
                            break
                            
                        try:
                            # Extract comment text
                            text_elem = comment_elem.find_element(By.CSS_SELECTOR, '#content-text')
                            comment_text = text_elem.text.strip() if text_elem else ''
                            
                            # Extract author
                            author_elem = comment_elem.find_element(By.CSS_SELECTOR, '#author-text')
                            author = author_elem.text.strip() if author_elem else ''
                            
                            # Extract likes
                            like_elem = comment_elem.find_elements(By.CSS_SELECTOR, '#vote-count-middle')
                            likes = like_elem[0].text.strip() if like_elem else '0'
                            
                            # Extract time
                            time_elem = comment_elem.find_elements(By.CSS_SELECTOR, '.published-time-text a')
                            time_posted = time_elem[0].text.strip() if time_elem else ''
                            
                            comment_data = {
                                'platform': 'youtube_comment',
                                'text': comment_text,
                                'author': author,
                                'likes': likes,
                                'time': time_posted,
                                'video_url': video_url
                            }
                            
                            # Check for duplicates
                            comment_exists = any(
                                existing_comment['text'] == comment_data['text'] and 
                                existing_comment['author'] == comment_data['author']
                                for existing_comment in comments
                            )
                            
                            if not comment_exists and comment_data['text']:
                                comments.append(comment_data)
                                print(f"Scraped comment {len(comments)}: {comment_data['author']} - {comment_data['text'][:30]}...")
                                
                        except Exception as e:
                            print(f"Error processing individual comment: {str(e)}")
                            continue
                    
                    # Scroll down to load more comments
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(3)
                    
                    new_height = driver.execute_script("return document.body.scrollHeight")
                    if new_height == last_height:
                        scroll_attempts += 1
                        time.sleep(2)
                    else:
                        scroll_attempts = 0
                        
                    last_height = new_height
                    
                except Exception as e:
                    print(f"Error in YouTube comments scroll iteration: {str(e)}")
                    scroll_attempts += 1
                    time.sleep(2)

            driver.quit()
            return comments
            
        except Exception as e:
            if 'driver' in locals():
                driver.quit()
            return {"error": str(e)}

# Replace with real credentials for Twitter
TWITTER_USERNAME = "@DineshRaut55503"
TWITTER_PASSWORD = "Rdhobe@140599"

@app.route('/fetch-tweets', methods=['POST'])
def fetch_tweets():
    data = request.get_json()
    search_term = data.get('search_term', 'unknown')
    num_tweets = int(data.get('num_tweets', 10))
    
    scraper = SocialMediaScraper(TWITTER_USERNAME, TWITTER_PASSWORD)
    tweets = scraper.scrape_tweets(search_term, num_tweets)
    
    return jsonify(tweets)

@app.route('/fetch-youtube-videos', methods=['POST'])
def fetch_youtube_videos():
    data = request.get_json()
    search_term = data.get('search_term', 'unknown')
    num_videos = int(data.get('num_videos', 10))
    
    scraper = SocialMediaScraper()
    videos = scraper.scrape_youtube_videos(search_term, num_videos)
    
    return jsonify(videos)

@app.route('/fetch-youtube-comments', methods=['POST'])
def fetch_youtube_comments():
    data = request.get_json()
    video_url = data.get('video_url', '')
    num_comments = int(data.get('num_comments', 50))
    
    if not video_url:
        return jsonify({"error": "video_url is required"})
    
    scraper = SocialMediaScraper()
    comments = scraper.scrape_youtube_comments(video_url, num_comments)
    
    return jsonify(comments)

@app.route('/fetch-all', methods=['POST'])
def fetch_all():
    """Fetch both Twitter and YouTube data for a search term"""
    data = request.get_json()
    search_term = data.get('search_term', 'unknown')
    num_tweets = int(data.get('num_tweets', 10))
    num_videos = int(data.get('num_videos', 10))
    
    scraper = SocialMediaScraper(TWITTER_USERNAME, TWITTER_PASSWORD)
    
    results = {
        'search_term': search_term,
        'tweets': [],
        'youtube_videos': []
    }
    
    # Fetch Twitter data
    try:
        tweets = scraper.scrape_tweets(search_term, num_tweets)
        if isinstance(tweets, list):
            results['tweets'] = tweets
        else:
            results['tweets'] = {"error": tweets.get("error", "Unknown Twitter error")}
    except Exception as e:
        results['tweets'] = {"error": str(e)}
    
    # Fetch YouTube data
    try:
        videos = scraper.scrape_youtube_videos(search_term, num_videos)
        if isinstance(videos, list):
            results['youtube_videos'] = videos
        else:
            results['youtube_videos'] = {"error": videos.get("error", "Unknown YouTube error")}
    except Exception as e:
        results['youtube_videos'] = {"error": str(e)}
    
    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=False, port=5000)