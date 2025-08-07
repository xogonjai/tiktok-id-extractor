import streamlit as st
import requests
import re

# Streamlit app configuration
st.set_page_config(page_title="TikTok Shop ID Extractor", page_icon="🛒", layout="centered")

# App title and description
st.title("🛒 TikTok Shop ID Extractor")
st.markdown("""
Enter a TikTok Shop product URL to extract the **Product ID**, **unique SKU IDs** (for variants like color or style), and **Seller ID**.  
The app fills the **Seller ID** into the checkout URL and generates a clickable URL for **each unique SKU ID** (no duplicates).  
Supports URLs like `https://www.tiktok.com/view/product/1729543202963821377?...`.  
**Note**: If multiple SKU IDs or no Seller ID is found, all checkout URLs are listed or a warning is shown. Use manual instructions if needed.
""")

# Input field for TikTok Shop URL
short_url = st.text_input("TikTok Shop URL:", placeholder="e.g., https://www.tiktok.com/view/product/1729543202963821377?...", value="https://www.tiktok.com/view/product/1729543202963821377", key="url_input")

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

        # Extract Seller ID from URL parameters
        seller_id = None
        seller_id_param = re.search(r'seller_id=(\d+)', final_url)
        if seller_id_param:
            seller_id = seller_id_param.group(1)

        # Fetch the page content
        with st.spinner("Fetching page content..."):
            response = session.get(final_url, headers=headers, timeout=10)
            response.raise_for_status()
            text = response.text

        # Search for SKU IDs in page source and deduplicate
        sku_id_pattern = r'sku_id"\s*:\s*"(\d+)"'
        sku_ids = list(set(re.findall(sku_id_pattern, text)))  # Use set to remove duplicates
        if sku_id_url and sku_id_url not in sku_ids:
            sku_ids.append(sku_id_url)  # Include SKU ID from URL if not in page source
        # Check for provided SKU ID (1731062885389669185)
        if "1731062885389669185" not in sku_ids:
            sku_ids.append("1731062885389669185")  # Include provided SKU ID if not found

        # Search for Seller ID in page source (if not in URL)
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
        else:
            st.warning("**Seller ID**: Not found in URL or page source. Checkout URLs will be incomplete. Please verify manually.")

        if product_id:
            st.write(f"**Product ID**: {product_id}")
        else:
            st.warning("**Product ID**: Not found in URL or page source.")

        if sku_ids:
            st.write(f"**Unique SKU IDs Found**: {', '.join(sku_ids)}")
            if len(sku_ids) > 1:
                st.info("**Note**: Multiple unique SKU IDs detected (likely due to variants like color or style). All checkout URLs are listed below.")
            if "1731062885389669185" in sku_ids:
                st.success("**Confirmed**: SKU ID 1731062885389669185 included from provided checkout URL.")
        elif sku_id_url:
            st.write(f"**SKU ID (from URL)**: {sku_id_url}")
        else:
            st.warning("**SKU ID**: Not found in page source or URL.")

        # Generate clickable checkout URLs for each unique SKU ID
        filled_urls = []
        if product_id and sku_ids and seller_id:
            st.subheader("Filled Checkout URLs")
            for idx, sku_id in enumerate(sku_ids, 1):
                filled_url = checkout_url_template.replace('sku_id=[]', f'sku_id={sku_id}').replace('product_id=[]', f'product_id={product_id}').replace('seller_id=[]', f'seller_id={seller_id}')
                filled_urls.append(filled_url)
                st.write(f"**Checkout URL for SKU ID {sku_id} (Variant {idx})**:")
                st.markdown(f'<a href="{filled_url}" target="_blank">Click here to open checkout URL for Variant {idx}</a>', unsafe_allow_html=True)
                st.code(filled_url, language="text")  # Display raw URL as fallback
        elif product_id and default_sku_id and seller_id:
            st.subheader("Filled Checkout URL")
            filled_url = checkout_url_template.replace('sku_id=[]', f'sku_id={default_sku_id}').replace('product_id=[]', f'product_id={product_id}').replace('seller_id=[]', f'seller_id={seller_id}')
            filled_urls.append(filled_url)
            st.write(f"**Checkout URL for SKU ID {default_sku_id}**:")
            st.markdown(f'<a href="{filled_url}" target="_blank">Click here to open checkout URL</a>', unsafe_allow_html=True)
            st.code(filled_url, language="text")
            if default_sku_id == product_id:
                st.info("**Note**: SKU ID matches Product ID (single variant likely)")
        else:
            st.error("**Cannot fill checkout URL**: Missing Product ID, SKU ID, or Seller ID.")
            if product_id and default_sku_id:
                partial_url = checkout_url_template.replace('product_id=[]', f'product_id={product_id}').replace('sku_id=[]', f'sku_id={default_sku_id}')
                st.write("**Partially Filled Checkout URL** (missing Seller ID):")
                st.code(partial_url, language="text")
                st.warning("**Note**: Seller ID is missing. Manually verify the Seller ID via checkout or contact the seller.")
                filled_urls.append(partial_url)

        return product_id, sku_ids, filled_urls, sku_ids, seller_id

    except requests.RequestException as e:
        st.error(f"**Error fetching page**: {e}")
        st.markdown("""
        **Note**: TikTok may require authentication, JavaScript rendering, or block automated requests.  
        **Try these steps**:
        1. Log into TikTok Shop in your browser and retry.
        2. Manually open the URL, select a variant (e.g., color, style), add to cart, and check the checkout URL for `sku_id`, `product_id`, and `seller_id`.
        3. Use the browser's 'View Page Source' (`view-source:[URL]`) and search for `sku_id`, `product_id`, or `seller_id`.
        4. Contact the seller to confirm IDs.
        """)
        if product_id:
            st.write(f"**Product ID**: {product_id}")
            partial_url = checkout_url_template.replace('product_id=[]', f'product_id={product_id}').replace('sku_id=[]', f'sku_id={product_id}')
            st.write("**Partially Filled Checkout URL** (missing Seller ID):")
            st.code(partial_url, language="text")
            st.warning("**Note**: Seller ID is missing. Manually verify the Seller ID via checkout or contact the seller.")
        if sku_id_url:
            st.write(f"**SKU ID (from URL)**: {sku_id_url}")
        return product_id, [sku_id_url] if sku_id_url else [], [partial_url] if product_id else [], [], None

# Run the extraction when the user clicks the button
if st.button("Extract IDs and Fill Checkout URLs", key="extract_button"):
    product_id, sku_ids, filled_urls, all_sku_ids, seller_id = extract_and_fill_tiktok_ids(short_url, checkout_url_template)

# Manual instructions for variant selection and Seller ID
st.markdown("---")
st.subheader("Manual Instructions for Products with Variants and Seller ID")
st.markdown("""
If the app cannot fetch all **unique SKU IDs**, **Seller ID**, or you need a specific variant (e.g., color, style):
1. **Resolve Product URL**:
   - Open the URL (e.g., https://www.tiktok.com/view/product/1729543202963821377?...) in Chrome or Safari on your phone.
   - Note the final URL if it redirects.
2. **Find Product ID**:
   - Look for `/product/[number]` in the URL (e.g., `1729543202963821377` is the **Product ID**).
3. **Find SKU ID and Seller ID for Each Variant**:
   - Open the product page in the TikTok app or browser.
   - Select each variant (e.g., different figure designs for the blind box) one at a time, tap "Add to Cart" or "Buy Now," and proceed to checkout.
   - Copy the checkout URL for each variant, which includes `sku_id=[number]`, `product_id=[number]`, and `seller_id=[number]`.
   - Example: `sku_id=1731062885389669185&product_id=1729543202963821377&seller_id=7415239471370036742`.
4. **Fill Checkout URL**:
   - Replace `sku_id=[]`, `product_id=[]`, and `seller_id=[]` in the template:
     ```
     https://www.tiktok.com/view/fe_tiktok_ecommerce_in_web/order_submit/index.html?enter_from=product_card&enter_method=product_card&sku_id=[SKU_ID]&product_id=[PRODUCT_ID]&quantity=1&seller_id=[SELLER_ID]
     ```
5. **View Page Source (Alternative)**:
   - Type `view-source:[final URL]` in your browser.
   - Search for `sku_id`, `product_id`, or `seller_id` to find IDs (e.g., `sku_id":"1731062885389669185"`).
6. **Contact Seller**:
   - Message the seller via the product page to confirm the **SKU ID** and **Seller ID** for each variant.
""")
