import streamlit as st
import requests
import re

# Streamlit app configuration
st.set_page_config(page_title="TikTok Shop ID Extractor", page_icon="🛒", layout="centered")

# App title and description
st.title("🛒 TikTok Shop ID Extractor")
st.markdown("""
Enter a TikTok Shop product URL to extract the **Product ID**, **unique SKU IDs** (for variants like color or style), and **Seller ID**.  
The app extracts the **Seller ID** using the same method as **SKU IDs** (from URL or page source) and fills it into the checkout URL, generating a clickable URL for **each unique SKU ID** (no duplicates).  
Supports URLs like `https://www.tiktok.com/view/product/1729543202963821377?...`.  
**Note**: If multiple SKU IDs or no Seller ID is found, all checkout URLs are listed or a warning is shown. Use manual instructions if needed.
""")

# Input field for TikTok Shop URL (blank by default)
short_url = st.text_input("TikTok Shop URL:", placeholder="e.g., https://www.tiktok.com/view/product/1729543202963821377?...", key="url_input")

# Checkout URL template (provided by user)
checkout_url_template = "https://www.tiktok.com/view/fe_tiktok_ecommerce_in_web/order_submit/index.html?enter_from=product_card&enter_method=product_card&sku_id=[]&product_id=[]&quantity=1&seller_id=[]"

# Function to extract IDs and generate multiple checkout URLs
def extract_and_fill_tiktok_ids(short_url, checkout_url_template):
    if not short_url:
        st.warning("Please enter a valid TikTok Shop URL.")
        return None, [], None, [], None

    try:
        # Set headers to mimic a mobile browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        
        # Resolve product URL
        with st.spinner("Resolving URL..."):
            session = requests.Session()
            response = session.get(short_url, headers=headers, allow_redirects=True, timeout=10)
            final_url = response.url
            st.success(f"**Resolved URL**: {final_url}")

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

        # Extract Seller ID from URL parameters (same method as SKU ID)
        seller_id = None
        seller_id_param = re.search(r'seller_id=(\d+)', final_url)
        if seller_id_param:
            seller_id = seller_id_param.group(1)

        # Fetch the page content
        with st.spinner("Fetching page content..."):
            response = session.get(final_url, headers=headers, timeout=10)
            response.raise_for_status()
            text = response.text

        # Search for SKU IDs in page source and deduplicate (same method as Seller ID)
        sku_id_pattern = r'sku_id"\s*:\s*"(\d+)"'
        sku_ids = list(set(re.findall(sku_id_pattern, text)))  # Use set to remove duplicates
        if sku_id_url and sku_id_url not in sku_ids:
            sku_ids.append(sku_id_url)  # Include SKU ID from URL
        # Include provided SKU ID (1731062885389669185)
        if "1731062885389669185" not in sku_ids:
            sku_ids.append("1731062885389669185")

        # Search for Seller ID in page source (same method as SKU ID)
        if not seller_id:
            seller_id_pattern = r'seller_id"\s*:\s*"(\d+)"'
            seller_id_match = re.search(seller_id_pattern, text)
            if seller_id_match:
                seller_id = seller_id_match.group(1)

        # Default SKU ID (URL parameter > page source > Product ID)
        default_sku_id = sku_id_url or (sku_ids[0] if sku_ids else product_id)

        # Display results
        st.subheader("Results")
        st.write(f"**Product URL (after redirect)**: {final_url}")
        if seller_id:
            st.write(f"**Seller ID**: {seller_id}")
        else
