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
**Note**: If multiple SKU IDs or no Seller ID is found, all checkout URLs are listed or a warning is shown.
""")

# Checkout URL base
CHECKOUT_URL_BASE = "https://www.tiktok.com/view/fe_tiktok_ecommerce_in_web/order_submit/index.html?enter_from=product_card&enter_method=product_card"

# Function to extract IDs
def extract_and_fill_tiktok_ids(short_url):
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
            seller_id_pattern = r'(?:"seller_id"|"sellerId"|"shop_id"|"merchant_id"|"store_id")\s*:\s*"(\d+)"'
            seller_id_match = re.search(seller_id_pattern, text)
            if seller_id_match:
                seller_id = seller_id_match.group(1)
            else:
                st.warning("Seller ID not found in page source. Final URL: " + final_url)
                st.code(text[:1500], language="html")  # Debug: Show first 1500 characters

        # Default SKU ID
        default_sku_id = sku_id_url or (sku_ids[0] if sku_ids else product_id)

        # Generate checkout URLs for quantities 1, 2, 6
        quantities = [1, 2, 6]
        if product_id and default_sku_id and seller_id:
            if len(sku_ids) > 1:
                for sku_id in sku_ids:
                    for qty in quantities:
                        filled_url = f"{CHECKOUT_URL_BASE}&sku_id={sku_id}&product_id={product_id}&quantity={qty}&seller_id={seller_id}"
                        filled_urls.append((sku_id, qty, filled_url))
            else:
                for qty in quantities:
                    filled_url = f"{CHECKOUT_URL_BASE}&sku_id={default_sku_id}&product_id={product_id}&quantity={qty}&seller_id={seller_id}"
                    filled_urls.append((default_sku_id, qty, filled_url))

        return product_id, sku_ids, filled_urls, default_sku_id, seller_id

    except requests.HTTPError as e:
        st.error(f"HTTP error occurred: {str(e)}")
        if e.response.status_code == 403:
            st.warning("Access denied (403). TikTok may require authentication or block automated requests. Try a different browser or device.")
        elif e.response.status_code == 429:
            st.warning("Too many requests (429). Please try again later.")
        if 'text' in locals():
            st.code(text[:1500], language="html")  # Debug: Show page source sample
        return None, [], [], None, None
    except requests.Timeout:
        st.error("Request timed out. TikTok servers may be slow or unreachable.")
        return None, [], [], None, None
    except requests.RequestException as e:
        st.error(f"Error fetching page: {str(e)}")
        return None, [], [], None, None
    except Exception as e:
        st.error(f"Unexpected error: {str(e)}")
        return None, [], [], None, None

# Input field and button
short_url = st.text_input("TikTok Shop URL:", placeholder="e.g., https://www.tiktok.com/view/product/1729543202963821377?...", key="url_input")
if st.button("Extract IDs and Fill Checkout URLs", key="extract_button"):
    product_id, sku_ids, filled_urls, default_sku_id, seller_id = extract_and_fill_tiktok_ids(short_url)

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
        if len(sku_ids) > 1:
            for idx, sku_id in enumerate(sku_ids, 1):
                st.write(f"**Checkout URLs for SKU ID {sku_id} (Variant {idx})**:")
                for _, qty, filled_url in [item for item in filled_urls if item[0] == sku_id]:
                    st.markdown(f'<a href="{filled_url}" target="_blank">Click here to open checkout URL for Quantity {qty}</a>', unsafe_allow_html=True)
                    st.code(filled_url, language="text")
        else:
            st.write(f"**Checkout URLs for SKU ID {default_sku_id}**:")
            for _, qty, filled_url in filled_urls:
                st.markdown(f'<a href="{filled_url}" target="_blank">Click here to open checkout URL for Quantity {qty}</a>', unsafe_allow_html=True)
                st.code(filled_url, language="text")
            if default_sku_id == product_id:
                st.info("SKU ID matches Product ID (likely a single-variant product).")
            if default_sku_id == "1729648752805187592":
                st.success("Confirmed: SKU ID matches previously provided value 1729648752805187592.")
    elif product_id and default_sku_id:
        st.subheader("Partially Filled Checkout URL")
        quantities = [1, 2, 6]
        for qty in quantities:
            partial_url = f"{CHECKOUT_URL_BASE}&sku_id={default_sku_id}&product_id={product_id}&quantity={qty}&seller_id=[SELLER_ID]"
            st.code(partial_url, language="text")
        st.warning("Seller ID missing. Manually verify via checkout or contact the seller.")
    else:
        st.error("Cannot generate checkout URLs: Missing required IDs.")
