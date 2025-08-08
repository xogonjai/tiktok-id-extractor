import streamlit as st
import requests
import re

# Streamlit app configuration
st.set_page_config(page_title="TikTok Shop ID Extractor", page_icon="🛒", layout="centered")

# App title and description
st.title("🛒 TikTok Shop ID Extractor")
st.markdown("""
Enter a TikTok Shop product URL to extract the **Product ID**, **unique SKU IDs** (for variants like color or style), and **Seller ID**.  
The app identifies whether the product has a **Single Variant** (one SKU) or a **Set of Variants** (multiple SKUs) and generates a clickable checkout URL for each unique SKU ID.  
Supported URLs: `https://www.tiktok.com/view/product/1729543202963821377?...`.  
**Note**: If multiple SKU IDs or no Seller ID is found, all checkout URLs are listed or a warning is shown. Use manual instructions if needed.
""")

# Checkout URL template
CHECKOUT_URL_TEMPLATE = "https://www.tiktok.com/view/fe_tiktok_ecommerce_in_web/order_submit/index.html?enter_from=product_card&enter_method=product_card&sku_id=[]&product_id=[]&quantity=1&seller_id={}"

# Toggle for playwright (for dynamic content)
use_playwright = st.checkbox("Use Playwright for dynamic content (requires installation)", value=False)

# Function to extract IDs
def extract_and_fill_tiktok_ids(short_url, use_playwright=False):
    if not short_url:
        st.warning("Please enter a valid TikTok Shop URL.")
        return None, [], [], None, None

    # Basic URL validation
    if not short_url.startswith(('http://', 'https://')) or 'tiktok.com' not in short_url:
        st.error("Invalid URL. Please provide a TikTok Shop URL (e.g., https://www.tiktok.com/view/product/...).")
        return None, [], [], None, None

    try:
        # Initialize variables to avoid NameError
        product_id = None
        sku_id_url = None
        seller_id = None
        sku_ids = []
        filled_urls = []

        # Fetch page content
        with st.spinner("Fetching TikTok Shop data..."):
            if use_playwright:
                try:
                    from playwright.sync_api import sync_playwright
                    with sync_playwright() as p:
                        browser = p.chromium.launch()
                        page = browser.new_page()
                        page.goto(short_url)
                        text = page.content()
                        browser.close()
                except ImportError:
                    st.error("Playwright not installed. Run `pip install playwright` and `playwright install`.")
                    return None, [], [], None, None
            else:
                session = requests.Session()
                headers = {
                    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
                }
                response = session.get(short_url, headers=headers, allow_redirects=True, timeout=10)
                response.raise_for_status()
                final_url = response.url
                text = response.text

        # Extract Product ID from URL
        product_id_match = re.search(r'/product/(\d+)', final_url)
        if product_id_match:
            product_id = product_id_match.group(1)
        else:
            product_id_param = re.search(r'product_id=(\d+)', final_url)
            if product_id_param:
                product_id = product_id_param.group(1)

        # Extract SKU ID from URL parameters
        sku_id_param = re.search(r'sku_id=(\d+)', final_url)
        if sku_id_param:
            sku_id_url = sku_id_param.group(1)

        # Extract Seller ID from URL parameters
        seller_id_param = re.search(r'seller_id=(\d+)', final_url)
        if seller_id_param:
            seller_id = seller_id_param.group(1)

        # Search for SKU IDs in page source
        sku_id_pattern = r'sku_id"\s*:\s*"(\d+)"'
        sku_ids = list(set(re.findall(sku_id_pattern, text)))
        if sku_id_url and sku_id_url not in sku_ids:
            sku_ids.append(sku_id_url)

        # Search for Seller ID in page source (if not in URL)
        if not seller_id:
            seller_id_pattern = r'(?:"seller_id"|"sellerId"|"shop_id"|"merchant_id")\s*:\s*"(\d+)"'
            seller_id_match = re.search(seller_id_pattern, text)
            if seller_id_match:
                seller_id = seller_id_match.group(1)
            else:
                st.warning("Seller ID not found in page source. Final URL: " + final_url)
                st.code(text[:1000], language="html")  # Debug: Show first 1000 characters

        # Default SKU ID
        default_sku_id = sku_id_url or (sku_ids[0] if sku_ids else product_id)

        # Generate checkout URLs
        if product_id and default_sku_id and seller_id:
            if len(sku_ids) > 1:
                for sku_id in sku_ids:
                    filled_url = CHECKOUT_URL_TEMPLATE.format(seller_id).replace('sku_id=[]', f'sku_id={sku_id}').replace('product_id=[]', f'product_id={product_id}')
                    filled_urls.append(filled_url)
            else:
                filled_url = CHECKOUT_URL_TEMPLATE.format(seller_id).replace('sku_id=[]', f'sku_id={default_sku_id}').replace('product_id=[]', f'product_id={product_id}')
                filled_urls.append(filled_url)

        return product_id, sku_ids, filled_urls, default_sku_id, seller_id

    except requests.HTTPError as e:
        st.error(f"HTTP error occurred: {str(e)}")
        if e.response.status_code == 403:
            st.warning("Access denied (403). TikTok may require authentication or block automated requests. Try enabling Playwright.")
        elif e.response.status_code == 429:
            st.warning("Too many requests (429). Please try again later.")
        st.info("Try opening the URL in a browser, adding the product to cart, and checking the checkout URL for `seller_id`. Alternatively, use `view-source:[URL]` to search for `seller_id`.")
        if 'text' in locals():
            st.code(text[:1000], language="html")  # Debug: Show page source sample
    except requests.Timeout:
        st.error("Request timed out. TikTok servers may be slow or unreachable.")
    except requests.RequestException as e:
        st.error(f"Error fetching page: {str(e)}")
    except Exception as e:
        st.error(f"Unexpected error: {str(e)}")
    st.markdown("""
    **Troubleshooting**:
    - Log into TikTok Shop in your browser and retry.
    - Open the URL, select a variant, add to cart, and check the checkout URL for IDs.
    - Use `view-source:[URL]` in your browser and search for `sku_id`, `product_id`, `seller_id`, `shop_id`, or `merchant_id`.
    - Contact the seller for confirmation.
    """)
    return product_id, sku_ids, filled_urls, default_sku_id, seller_id

# Input field and button
short_url = st.text_input("TikTok Shop URL:", placeholder="e.g., https://www.tiktok.com/view/product/1729543202963821377?...", key="url_input")
if st.button("Extract IDs and Fill Checkout URLs", key="extract_button"):
    product_id, sku_ids, filled_urls, default_sku_id, seller_id = extract_and_fill_tiktok_ids(short_url, use_playwright)

    # Display results
    st.subheader("Results")
    if product_id:
        st.write(f"**Product ID**: {product_id}")
    else:
        st.warning("**Product ID**: Not found in URL or page source.")

    if seller_id:
        st.write(f"**Seller ID**: {seller_id}")
    else:
        st.warning("**Seller ID**: Not found in URL or page source. Checkout URLs may be incomplete.")
        st.info("Try opening the URL in a browser, adding the product to cart, and checking the checkout URL for `seller_id`. Alternatively, use `view-source:[URL]` to search for `seller_id`, `shop_id`, or `merchant_id`.")

    if sku_ids:
        st.write(f"**Unique SKU IDs Found**: {', '.join(sku_ids)}")
        # Identify single vs. set of variants
        if len(sku_ids) == 1 or (sku_ids and sku_ids[0] == product_id):
            st.success("**Variant Type**: Single Variant (one SKU detected or SKU matches Product ID)")
        else:
            st.info("**Variant Type**: Set of Variants (multiple SKUs detected, likely different colors or styles)")
    else:
        st.warning("**SKU ID**: Not found in page source or URL.")

    # Display checkout URLs
    if filled_urls:
        st.subheader("Filled Checkout URLs")
        if len(filled_urls) > 1:
            for idx, filled_url in enumerate(filled_urls, 1):
                sku_id = sku_ids[idx-1]
                st.write(f"**Checkout URL for SKU ID {sku_id} (Variant {idx})**:")
                st.markdown(f'<a href="{filled_url}" target="_blank">Click here to open checkout URL for Variant {idx}</a>', unsafe_allow_html=True)
                st.code(filled_url, language="text")
        else:
            st.write(f"**Checkout URL for SKU ID {default_sku_id}**:")
            st.markdown(f'<a href="{filled_urls[0]}" target="_blank">Click here to open checkout URL</a>', unsafe_allow_html=True)
            st.code(filled_urls[0], language="text")
            if default_sku_id == product_id:
                st.info("SKU ID matches Product ID (likely a single-variant product).")
            if default_sku_id == "1729648752805187592":
                st.success("Confirmed: SKU ID matches previously provided value 1729648752805187592.")
    elif product_id and default_sku_id:
        st.subheader("Partially Filled Checkout URL")
        partial_url = CHECKOUT_URL_TEMPLATE.format("[SELLER_ID]").replace('sku_id=[]', f'sku_id={default_sku_id}').replace('product_id=[]', f'product_id={product_id}')
        st.code(partial_url, language="text")
        st.warning("Seller ID missing. Manually verify via checkout or contact the seller.")
    else:
        st.error("Cannot generate checkout URLs: Missing required IDs.")

# Collapsible manual instructions
with st.expander("Manual Instructions for Products with Variants"):
    st.markdown("""
    If the app cannot fetch **unique SKU IDs** or **Seller ID**:
    1. **Resolve Product URL**:
       - Open the URL (e.g., https://www.tiktok.com/view/product/1729543202963821377?...) in Chrome or Safari.
       - Note the final URL if it redirects.
    2. **Find Product ID**:
       - Look for `/product/[number]` in the URL (e.g., `1729543202963821377` is the **Product ID**).
    3. **Find SKU ID and Seller ID**:
       - Open the product page in the TikTok app or browser.
       - Select each variant (e.g., color, style), tap "Add to Cart" or "Buy Now," and proceed to checkout.
       - Copy the checkout URL, which includes `sku_id=[number]`, `product_id=[number]`, and `seller_id=[number]`.
       - Example: `sku_id=1729543202963821500&product_id=1729543202963821377&seller_id=7415239471370036742`.
    4. **Fill Checkout URL**:
       - Replace `sku_id=[]`, `product_id=[]`, and `seller_id={}` in the template:
         ```
         https://www.tiktok.com/view/fe_tiktok_ecommerce_in_web/order_submit/index.html?enter_from=product_card&enter_method=product_card&sku_id=[SKU_ID]&product_id=[PRODUCT_ID]&quantity=1&seller_id=[SELLER_ID]
         ```
    5. **View Page Source (Alternative)**:
       - Type `view-source:[final URL]` in your browser.
       - Search for `sku_id`, `product_id`, `seller_id`, `shop_id`, or `merchant_id`.
    6. **Contact Seller**:
       - Message the seller via the product page to confirm **SKU ID** and **Seller ID**.
    """)

# Optional: Headless browser integration (commented out, requires `playwright` installation)
"""
# Requires: pip install playwright; playwright install
from playwright.sync_api import sync_playwright
def extract_with_playwright(url):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)
        text = page.content()
        browser.close()
        return text
# Replace `response.text` with `extract_with_playwright(short_url)` in the try block if needed.
"""
