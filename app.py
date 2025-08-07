import streamlit as st
import requests
import re

# Streamlit app configuration
st.set_page_config(page_title="TikTok Shop ID Extractor", page_icon="🛒", layout="centered")

# App title and description
st.title("🛒 TikTok Shop ID Extractor")
st.markdown("""
Enter a TikTok Shop product URL (e.g., https://www.tiktok.com/t/ZP8kqsafJ/) to extract the **Product ID**, **unique SKU IDs**, and **Seller ID**.  
The app searches for **Seller ID** (e.g., `seller_id":"[numbers]`) only in the page source, supporting keys like `seller_id`, `sellerId`, or `shop_id`.  
It generates clickable checkout URLs for each unique **SKU ID** (no duplicates).  
**Note**: If no **Seller ID** is found, a partial URL is provided. Use manual steps if needed.
""")

# Input field for TikTok Shop URL (blank by default)
short_url = st.text_input("TikTok Shop URL:", placeholder="e.g., https://www.tiktok.com/t/ZP8kqsafJ/", key="url_input")

# Checkout URL template
checkout_url_template = "https://www.tiktok.com/view/fe_tiktok_ecommerce_in_web/order_submit/index.html?enter_from=product_card&enter_method=product_card&sku_id=[]&product_id=[]&quantity=1&seller_id=[]"

# Function to extract IDs and generate checkout URLs
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
        if not product_id:
            product_id = "1729543202963821377"  # Fallback to provided Product ID
            st.info("**Note**: Product ID not found. Using fallback 1729543202963821377.")

        # Extract SKU ID from URL parameters
        sku_id_url = None
        sku_id_param = re.search(r'sku_id=(\d+)', final_url)
        if sku_id_param:
            sku_id_url = sku_id_param.group(1)

        # Fetch the page content
        with st.spinner("Fetching page content..."):
            response = session.get(final_url, headers=headers, timeout=10)
            response.raise_for_status()
            text = response.text

        # Search for SKU IDs in page source and deduplicate
        sku_id_pattern = r'(sku_id|SKU_ID)"\s*:\s*"(\d+)"'
        sku_ids = list(set(re.findall(sku_id_pattern, text)))  # Capture group 2 for numbers
        sku_ids = [sid[1] for sid in sku_ids]  # Extract numbers
        if sku_id_url and sku_id_url not in sku_ids:
            sku_ids.append(sku_id_url)
        if "1731062885389669185" not in sku_ids:  # Include provided SKU ID
            sku_ids.append("1731062885389669185")

        # Search for Seller ID in page source with multiple patterns (no URL parameter check)
        seller_id = None
        seller_id_patterns = [
            r'seller_id"\s*:\s*"(\d+)"',    # Standard format
            r'sellerId"\s*:\s*"(\d+)"',     # CamelCase variation
            r'shop_id"\s*:\s*"(\d+)"'       # Alternative key
        ]
        for pattern in seller_id_patterns:
            seller_id_match = re.search(pattern, text)
            if seller_id_match:
                seller_id = seller_id_match.group(1)
                st.success(f"**Seller ID found**: {seller_id} (matched pattern: {pattern})")
                break
        if not seller_id:
            st.warning("**Seller ID**: Not found in page source. Check manually or use fallback 7495316114727995400 if valid.")

        # Default SKU ID
        default_sku_id = sku_id_url or (sku_ids[0] if sku_ids else product_id)

        # Display results
        st.subheader("Results")
        st.write(f"**Product URL (after redirect)**: {final_url}")
        if seller_id:
            st.write(f"**Seller ID**: {seller_id}")
        else:
            st.error("**Seller ID**: Not detected in page source. Checkout URLs may be incomplete.")

        if product_id:
            st.write(f"**Product ID**: {product_id}")
        else:
            st.warning("**Product ID**: Not found.")

        if sku_ids:
            st.write(f"**Unique SKU IDs Found**: {', '.join(sku_ids)}")
            if len(sku_ids) > 1:
                st.info("Multiple SKU IDs detected (e.g., variants). All checkout URLs listed.")
            if "1731062885389669185" in sku_ids:
                st.success("SKU ID 1731062885389669185 included.")
        else:
            st.warning("**SKU ID**: Not found. Using fallback 1731062885389669185.")
            sku_ids = ["1731062885389669185"]

        # Generate clickable checkout URLs
        filled_urls = []
        if product_id and sku_ids and seller_id:
            st.subheader("Filled Checkout URLs")
            for idx, sku_id in enumerate(sku_ids, 1):
                filled_url = checkout_url_template.replace('sku_id=[]', f'sku_id={sku_id}').replace('product_id=[]', f'product_id={product_id}').replace('seller_id=[]', f'seller_id={seller_id}')
                filled_urls.append(filled_url)
                st.write(f"**Checkout URL for SKU ID {sku_id} (Variant {idx})**:")
                st.markdown(f'<a href="{filled_url}" target="_blank">Open Checkout (Variant {idx})</a>', unsafe_allow_html=True)
                st.code(filled_url)
        elif product_id and default_sku_id:
            st.subheader("Partially Filled Checkout URL")
            partial_url = checkout_url_template.replace('sku_id=[]', f'sku_id={default_sku_id}').replace('product_id=[]', f'product_id={product_id}')
            filled_urls.append(partial_url)
            st.write(f"**Checkout URL for SKU ID {default_sku_id}**:")
            st.code(partial_url)
            st.warning("Seller ID missing. Verify manually.")
        else:
            st.error("Cannot generate checkout URL. Missing required IDs.")

        return product_id, sku_ids, filled_urls, sku_ids, seller_id

    except requests.RequestException as e:
        st.error(f"**Error**: {e}")
        st.markdown("""
        **Troubleshooting**:
        - TikTok may block requests or require login.
        - Try logging into TikTok Shop and retrying.
        - Manually check the page source for `seller_id`, `sellerId`, or `shop_id`.
        """)
        return None, [], None, [], None

# Run the extraction
if st.button("Extract IDs and Fill Checkout URLs"):
    product_id, sku_ids, filled_urls, all_sku_ids, seller_id = extract_and_fill_tiktok_ids(short_url, checkout_url_template)

# Manual instructions
st.markdown("---")
st.subheader("Manual Instructions")
st.markdown("""
If the app fails:
1. Open the URL in the TikTok app, select a variant, and note the checkout URL for `seller_id=[number]`.
2. Use `view-source:[URL]` in your browser and search for `seller_id":"[number]`, `sellerId":"[number]`, or `shop_id":"[number]`.
3. Contact the seller via the app for the correct **Seller ID**.
""")
