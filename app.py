import streamlit as st
import requests
import re

# Streamlit app configuration
st.set_page_config(page_title="TikTok Shop ID Extractor", page_icon="🛒", layout="centered")

# App title and description
st.title("🛒 TikTok Shop ID Extractor")
st.markdown("""
Enter a TikTok Shop URL (shortened or product page) to extract the **Product ID** and **SKU ID**, 
and generate a filled checkout URL. Supports URLs like `https://www.tiktok.com/t/ZP8kqPRcB/` or 
`https://www.tiktok.com/view/product/[number]`.
""")

# Input field for TikTok Shop URL
short_url = st.text_input("TikTok Shop URL:", placeholder="e.g., https://www.tiktok.com/t/ZP8kqPRcB/", key="url_input")

# Checkout URL template
checkout_url_template = "https://www.tiktok.com/view/fe_tiktok_ecommerce_in_web/order_submit/index.html?enter_from=product_card&enter_method=product_card&sku_id=[]&product_id=[]&quantity=1&seller_id=7495316114727995400"

# Function to extract IDs and fill checkout URL
def extract_and_fill_tiktok_ids(short_url, checkout_url_template):
    if not short_url:
        st.warning("Please enter a valid TikTok Shop URL.")
        return None, None, None

    try:
        # Set headers to mimic a mobile browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        
        # Resolve shortened URL
        with st.spinner("Resolving URL..."):
            session = requests.Session()
            response = session.get(short_url, headers=headers, allow_redirects=True, timeout=10)
            final_url = response.url
            st.success(f"**Resolved URL**: {final_url}")

        # Extract Product ID from final URL
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

        # Fetch the page content
        with st.spinner("Fetching page content..."):
            response = session.get(final_url, headers=headers, timeout=10)
            response.raise_for_status()
            text = response.text

        # Search for SKU ID in page source
        sku_id_pattern = r'sku_id"\s*:\s*"(\d+)"'
        sku_ids = re.findall(sku_id_pattern, text)

        # Select SKU ID (URL parameter > page source > Product ID)
        sku_id = sku_id_url or (sku_ids[0] if sku_ids else product_id)

        # Display results
        st.subheader("Results")
        st.write(f"**Product URL (after redirect)**: {final_url}")
        if product_id:
            st.write(f"**Product ID**: {product_id}")
        else:
            st.warning("**Product ID**: Not found in URL or page source.")

        if sku_id:
            st.write(f"**SKU ID**: {sku_id}")
            if sku_id == product_id:
                st.info("**Note**: SKU ID matches Product ID (single variant likely)")
            if sku_id == "1729648752805187592":
                st.success("**Confirmed**: SKU ID matches previously provided value 1729648752805187592")
        else:
            st.warning("**SKU ID**: Not found in page source or URL.")

        # Fill the checkout URL
        if product_id and sku_id:
            filled_url = checkout_url_template.replace('sku_id=[]', f'sku_id={sku_id}').replace('product_id=[]', f'product_id={product_id}')
            st.write(f"**Filled Checkout URL**:")
            st.code(filled_url, language="text")
        else:
            st.error("**Cannot fill checkout URL**: Missing Product ID or SKU ID.")
            if product_id:
                partial_url = checkout_url_template.replace('product_id=[]', f'product_id={product_id}').replace('sku_id=[]', f'sku_id={product_id}')
                st.write(f"**Partially Filled Checkout URL** (using Product ID as fallback):")
                st.code(partial_url, language="text")

        return product_id, sku_id, filled_url if product_id and sku_id else None

    except requests.RequestException as e:
        st.error(f"**Error fetching page**: {e}")
        st.markdown("""
        **Note**: TikTok may require authentication, JavaScript rendering, or block automated requests.  
        **Try these steps**:
        1. Log into TikTok Shop in your browser and retry.
        2. Manually open the URL, add the product to cart, and check the checkout URL for `sku_id` and `product_id`.
        3. Use the browser's 'View Page Source' (`view-source:[URL]`) and search for `sku_id` or `product_id`.
        4. Contact the seller to confirm IDs.
        """)
        if product_id:
            st.write(f"**Product ID**: {product_id}")
            partial_url = checkout_url_template.replace('product_id=[]', f'product_id={product_id}').replace('sku_id=[]', f'sku_id={product_id}')
            st.write(f"**Partially Filled Checkout URL** (using Product ID as fallback):")
            st.code(partial_url, language="text")
        if sku_id_url:
            st.write(f"**SKU ID (from URL)**: {sku_id_url}")
        return product_id, sku_id_url, None

# Run the extraction when the user clicks the button
if st.button("Extract IDs and Fill Checkout URL", key="extract_button"):
    extract_and_fill_tiktok_ids(short_url, checkout_url_template)

# Manual instructions
st.markdown("---")
st.subheader("Manual Instructions (if app fails)")
st.markdown("""
If the app cannot fetch the IDs due to TikTok restrictions:
1. **Resolve Shortened URL**:
   - Open the URL (e.g., https://www.tiktok.com/t/ZP8kqPRcB/) in Chrome or Safari.
   - Note the final URL (e.g., https://www.tiktok.com/view/product/[number]).
2. **Find Product ID**:
   - Look for `/product/[number]` in the URL (e.g., `123456789` is the Product ID).
3. **Find SKU ID**:
   - On the product page, select a variant (e.g., size, color) and add to cart.
   - Check the checkout URL for `sku_id=[number]` and `product_id=[number]`.
   - Or, type `view-source:[final URL]` in the browser and search for `sku_id`.
4. **Fill Checkout URL**:
   - Replace `sku_id=[]` and `product_id=[]` in the template with the extracted IDs.
5. **Contact Seller**:
   - Message the seller via the product page to confirm IDs.
""")
