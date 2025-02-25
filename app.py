from flask import Flask, request, jsonify
from flask_cors import CORS
from bs4 import BeautifulSoup
import google.generativeai as genai
import requests
import os
from dotenv import load_dotenv
import re
from urllib.parse import urljoin
import logging
import time
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

load_dotenv()
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    raise ValueError("Missing GOOGLE_API_KEY environment variable")
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash-8b')

def clean_text(text):
    # Remove extra whitespace and newlines
    text = re.sub(r'\s+', ' ', text)
    # Remove special characters but keep punctuation
    text = re.sub(r'[^\w\s.,!?-]', '', text)
    return text.strip()

def extract_main_content(soup):
    # Remove unwanted elements
    for element in soup(['header', 'footer', 'nav', 'script', 'style', 'iframe', 'form']):
        element.decompose()
    
    # Try to find main content area
    main_content = soup.find('main') or soup.find('article') or soup.find('div', {'class': re.compile(r'content|main|article', re.I)})
    
    if (main_content):
        return main_content.get_text(separator=' ', strip=True)
    return soup.get_text(separator=' ', strip=True)

def scrape_url(url):
    logger.info(f"Starting to scrape URL: {url}")
    start_time = time.time()
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract title
        title = soup.title.string if soup.title else ''
        
        # Extract main content
        content = extract_main_content(soup)
        
        # Clean the extracted content
        cleaned_content = clean_text(content)
        
        # Extract links for potential context
        links = [urljoin(url, a.get('href')) for a in soup.find_all('a', href=True)]
        
        duration = time.time() - start_time
        logger.info(f"Successfully scraped URL: {url} (took {duration:.2f}s)")
        return {
            'title': title,
            'content': cleaned_content,
            'links': links[:5]  # Store first 5 related links
        }
    except Exception as e:
        logger.error(f"Error scraping {url}: {str(e)}")
        return {'error': f"Error scraping {url}: {str(e)}"}

@app.route('/', methods=['GET'])
def index():
    return jsonify({
        "status": "success",
        "message": "Server is running",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/fetch-content', methods=['POST'])
def fetch_content():
    start_time = time.time()
    logger.info(f"Received fetch-content request")
    
    try:
        urls = request.json.get('urls', [])
        logger.info(f"Processing {len(urls)} URLs")
        
        if not urls:
            logger.warning("No URLs provided in request")
            return jsonify({"error": "No URLs provided"}), 400
        
        content = {}
        for url in urls:
            if url.strip():
                result = scrape_url(url)
                if 'error' in result:
                    logger.error(f"Failed to scrape URL: {url}")
                    return jsonify({"error": result['error']}), 400
                content[url] = result
        
        duration = time.time() - start_time
        logger.info(f"Completed fetch-content request successfully in {duration:.2f}s")
        return jsonify({"content": content})
    except Exception as e:
        logger.error(f"Error in fetch-content: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/ask-question', methods=['POST'])
def ask_question():
    start_time = time.time()
    logger.info("Received ask-question request")
    
    try:
        data = request.json
        content = data.get('content', {})
        question = data.get('question', '').strip()
        
        logger.info(f"Processing question: '{question}'")
        logger.info(f"Content sources: {len(content)} URLs")
        
        if not content:
            logger.warning("No content provided in request")
            return jsonify({"error": "No content provided"}), 400
        if not question:
            logger.warning("No question provided in request")
            return jsonify({"error": "No question provided"}), 400
        
        # Prepare structured context for Gemini
        context_parts = []
        for url, data in content.items():
            if isinstance(data, dict) and 'title' in data and 'content' in data:
                context_parts.append(f"""
Source: {url}
Title: {data['title']}
Content:
{data['content'][:1500]}  # Limit content length per URL
                """)
        
        context = "\n\n---\n\n".join(context_parts)
        
        prompt = f"""You are a knowledgeable and thorough research assistant. Analyze the provided content and answer the question comprehensively.

Question: {question}

Reference Content:
{context}

Please provide a detailed response following this structure:

1. Direct Answer:
   - Begin with a clear, direct answer to the question
   - Highlight key points and main findings

2. Supporting Evidence:
   - Quote relevant passages from the source material using quotation marks
   - Cite the specific source URL for each quote
   - Explain how each piece of evidence supports the answer

3. Analysis & Context:
   - Provide additional context or background information
   - Explain any important relationships or implications
   - Address any potential limitations or caveats

4. Summary:
   - Conclude with a brief summary of the key points
   - Highlight any remaining uncertainties or areas needing clarification

If the provided content doesn't contain sufficient information to answer the question:
- Clearly state what information is missing
- Explain what additional information would be needed
- Note any partial insights that can be drawn from the available content

Format your response using clear headings and bullet points for readability."""

        logger.info("Sending request to Gemini API")
        response = model.generate_content(prompt)
        
        if response and response.text:
            answer = response.text.strip()
            # Convert markdown-style headers to HTML
            answer = re.sub(r'^(\d+)\.\s+([^\n]+)', r'<h3>\1. \2</h3>', answer, flags=re.MULTILINE)
            # Add paragraph breaks
            answer = answer.replace("\n\n", "<br><br>")
            # Bold any quotes
            answer = re.sub(r'"([^"]*)"', r'<b>"\1"</b>', answer)
            # Create bullet points
            answer = re.sub(r'^-\s+', '• ', answer, flags=re.MULTILINE)
            
            return jsonify({"answer": answer})
        
        logger.error("No response generated from Gemini API")
        return jsonify({"error": "No response generated"}), 500
        
    except Exception as e:
        logger.error(f"Error in ask-question: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 3000))
    logger.info(f"Starting server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
