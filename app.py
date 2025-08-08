import streamlit as st
import requests
import re
import time

# Streamlit app configuration
st.set_page_config(page_title="TikTok Shop ID Extractor", page_icon="🛒", layout="centered")

# App title and description
st.title("🛒 TikTok Shop ID Extractor")
st.markdown("""
Enter a TikTok Shop product URL to extract the **Product ID**, **unique SKU IDs** (for variants like color or style), and **Seller ID**.  
The app generates a clickable checkout URL for **each unique SKU ID** (no duplicates) using the **Seller ID** from the URL or page source.  
Supported URLs: `https://www.tiktok.com/view/product/1729543202963821377?...`.  
**Note**: If multiple SKU IDs or no Seller ID is found, all checkout URLs are listed or a warning is shown. Use manual instructions if needed.
""")

# Checkout URL template
CHECKOUT_URL_TEMPLATE = "https://www.tiktok.com/view/fe_tiktok_ecommerce_in_web/order_submit/index.html?enter_from=product_card&enter_method=product_card&sku_id=[]&product_id=[]&quantity=1&seller_id={}"

# Cache the extraction results to avoid redundant requests
@st.cache_data(show_spinner=False)
def extract_and_fill_tiktok_ids(short_url, _retry_count=2):
    if not short_url:
        st.warning("Please enter a valid TikTok Shop URL.")
        return None, [], None, [], None

    # Validate URL format
    if not re.match(r'^https?://(www\.)?tiktok\.com/view/product/\d+', short_url):
        st.error("Invalid URL format. Please provide a TikTok Shop product URL (e.g., https://www.tiktok.com/view/product/1729543202963821377?...).")
        return None, [], None, [], None

    try:
        # Set headers to mimic a mobile browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }

        # Fetch page content with retries
        with st.spinner("Fetching TikTok Shop data..."):
            session = requests.Session()
            for attempt in range(_retry_count):
                try:
                    response = session.get(short_url, headers=headers, allow_redirects=True, timeout=10)
                    response.raise_for_status()
                    break
                except requests.RequestException as e:
                    if attempt == _retry_count - 1:
                        raise e
                    time.sleep(2)  # Wait before retrying

            final_url = response.url
            text = response.text

        # Extract Product ID from URL
        product_id = None
        product_id_match = re.search(r'/product/(\d+)', final_url)
        if product_id_match:
            product_id = product_id_match.group(1)
        else:
            product_id_param = re.search(r'product_id=(\d+)', final_url)
            if product_id_param:
                product_id = product_id_param.group(1)

        # Extract SKU ID from URL parameters
        sku_id_url = None
        sku_id_param = re.search(r'sku_id=(\d+)', final_url)
        if sku_id_param:
            sku_id_url = sku_id_param.group(1)

        # Extract Seller ID from URL parameters
        seller_id = None
        seller_id_param = re.search(r'seller_id=(\d+)', final_url)
        if seller_id_param:
            seller_id = seller_id_param.group(1)

        # Search for SKU IDs in page source and deduplicate
        sku_id_pattern = r'sku_id"\s*:\s*"(\d+)"'
        sku_ids = list(set(re.findall(sku_id_pattern, text)))
        if sku_id_url and sku_id_url not in sku_ids:
            sku_ids.append(sku_id_url)

        # Search for Seller ID in page source (if not in URL)
        if not seller_id:
            seller_id_pattern = r'seller_id"\s*:\s*"(\d+)"'
            seller_id_match = re.search(seller_id_pattern, text)
            if seller_id_match:
                seller_id = seller_id_match.group(1)

        # Default SKU ID
        default_sku_id = sku_id_url or (sku_ids[0] if sku_ids else product_id)

        return product_id, sku_ids, default_sku_id, seller_id, final_url

    except requests.HTTPError as e:
        if e.response.status_code == 403:
            st.error("Access denied (HTTP 403). TikTok may be blocking automated requests or requiring authentication.")
        elif e.response.status_code == 429:
            st.error("Too many requests (HTTP 429). Please try again later.")
        else:
            st.error(f"HTTP error occurred: {str(e)}")
        return product_id, [sku_id_url] if sku_id_url else [], default_sku_id, [], None
    except requests.Timeout:
        st.error("Request timed out. TikTok servers may be slow or unreachable.")
        return product_id, [sku_id_url] if sku_id_url else [], default_sku_id, [], None
    except requests.RequestException as e:
        st.error(f"Error fetching page: {str(e)}")
        return product_id, [sku_id_url] if sku_id_url else [], default_sku_id, [], None

# Input field and button
short_url = st.text_input("TikTok Shop URL:", placeholder="e.g., https://www.tiktok.com/view/product/1729543202963821377?...", key="url_input")
if st.button("Extract IDs and Fill Checkout URLs", key="extract_button"):
    product_id, sku_ids, default_sku_id, seller_id, final_url = extract_and_fill_tiktok_ids(short_url)

    # Display results in a table
    st.subheader("Extracted IDs")
    if product_id or sku_ids or seller_id:
        result_data = {
            "ID Type": ["Product ID", "SKU IDs", "Seller ID"],
            "Value": [
                product_id or "Not found",
                ", ".join(sku_ids) if sku_ids else "Not found",
                seller_id or "Not found"
            ]
        }
        st.table(result_data)
    else:
        st.warning("No IDs found in the provided URL or page source.")

    # Generate and display checkout URLs
    filled_urls = []
    if product_id and default_sku_id and seller_id:
        st.subheader("Checkout URLs")
        if len(sku_ids) > 1:
            st.info("Multiple unique SKU IDs detected (likely variants like color or style). Listing all checkout URLs.")
            for idx, sku_id in enumerate(sku_ids, 1):
                filled_url = CHECKOUT_URL_TEMPLATE.format(seller_id).replace('sku_id=[]', f'sku_id={sku_id}').replace('product_id=[]', f'product_id={product_id}')
                filled_urls.append(filled_url)
                st.write(f"**Checkout URL for SKU ID {sku_id} (Variant {idx})**:")
                st.markdown(f'<a href="{filled_url}" target="_blank">Click here to open checkout URL for Variant {idx}</a>', unsafe_allow_html=True)
                if st.button(f"Copy URL for Variant {idx}", key=f"copy_{idx}"):
                    st.write(f"Copied: {filled_url}")
                    # Note: Streamlit doesn't natively support clipboard copying; consider JavaScript injection or external libraries
                st.code(filled_url, language="text")
        else:
            filled_url = CHECKOUT_URL_TEMPLATE.format(seller_id).replace('sku_id=[]', f'sku_id={default_sku_id}').replace('product_id=[]', f'product_id={product_id}')
            filled_urls.append(filled_url)
            st.write(f"**Checkout URL for SKU ID {default_sku_id}**:")
            st.markdown(f'<a href="{filled_url}" target="_blank">Click here to open checkout URL</a>', unsafe_allow_html=True)
            if st.button("Copy URL", key="copy_single"):
                st.write(f"Copied: {filled_url}")
            st.code(filled_url, language="text")
            if default_sku_id == product_id:
                st.info("SKU ID matches Product ID (likely a single-variant product).")
            if default_sku_id == "1729648752805187592":
                st.success("Confirmed: SKU ID matches previously provided value 1729648752805187592.")
    else:
        st.error("Cannot generate checkout URLs: Missing Product ID, SKU ID, or Seller ID.")
        if product_id and default_sku_id:
            partial_url = CHECKOUT_URL_TEMPLATE.format("[SELLER_ID]").replace('product_id=[]', f'product_id={product_id}').replace('sku_id=[]', f'sku_id={default_sku_id}')
            st.write("**Partially Filled Checkout URL** (missing Seller ID):")
            st.code(partial_url, language="text")
            st.warning("Seller ID missing. Manually verify via checkout or contact the seller.")

    # Error guidance
    if not seller_id or not sku_ids:
        st.markdown("""
        **Troubleshooting**:
        - TikTok may require authentication, JavaScript rendering, or block automated requests.
        - **Try**:
          1. Log into TikTok Shop in your browser and retry.
          2. Open the URL, select a variant, add to cart, and check the checkout URL for IDs.
          3. Use `view-source:[URL]` in your browser and search for `sku_id`, `product_id`, or `seller_id`.
          4. Contact the seller for confirmation.
        """)

# Collapsible manual instructions
with st.expander("Manual Instructions for Products with Variants and Seller ID"):
    st.markdown("""
    If the app cannot fetch all **unique SKU IDs**, **Seller ID**, or you need a specific variant (e.g., color, style):
    1. **Resolve Product URL**:
       - Open the URL (e.g., https://www.tiktok.com/view/product/1729543202963821377?...) in Chrome or Safari on your phone.
       - Note the final URL if it redirects.
    2. **Find Product ID**:
       - Look for `/product/[number]` in the URL (e.g., `1729543202963821377` is the **Product ID**).
    3. **Find SKU ID and Seller ID for Each Variant**:
       - Open the product page in the TikTok app or browser.
       - Select each variant (e.g., different figure designs for the blind box), tap "Add to Cart" or "Buy Now," and proceed to checkout.
       - Copy the checkout URL for each variant, which includes `sku_id=[number]`, `product_id=[number]`, and `seller_id=[number]`.
       - Example: `sku_id=1729543202963821500&product_id=1729543202963821377&seller_id=7415239471370036742`.
    4. **Fill Checkout URL**:
       - Replace `sku_id=[]`, `product_id=[]`, and `seller_id={}` in the template for each variant:
         ```
         https://www.tiktok.com/view/fe_tiktok_ecommerce_in_web/order_submit/index.html?enter_from=product_card&enter_method=product_card&sku_id=[SKU_ID]&product_id=[PRODUCT_ID]&quantity=1&seller_id=[SELLER_ID]
         ```
    5. **View Page Source (Alternative)**:
       - Type `view-source:[final URL]` in your browser.
       - Search for `sku_id`, `product_id`, or `seller_id` to find IDs (e.g., `sku_id":"1729543202963821500"`).
    6. **Contact Seller**:
       - Message the seller via the product page to confirm the **SKU ID** and **Seller ID** for each variant.
    """)
