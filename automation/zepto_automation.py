from playwright.sync_api import sync_playwright

# ================= PLAYWRIGHT AUTOMATION =================
def run_zepto(items, user_id):
    print("FUNCTION STARTED")

    from playwright.sync_api import sync_playwright
    import os, traceback
    from datetime import datetime

    p = sync_playwright().start()
    context = None

    try:
        print("Playwright initialized")

        context = p.chromium.launch_persistent_context(
            user_data_dir="zepto_user_data",
            headless=False,
            args=["--window-size=1920,1080"],
            viewport=None
        )

        page = context.pages[0] if context.pages else context.new_page()

        page.goto("https://www.zepto.com/")
        page.wait_for_timeout(3000)

        print("TOTAL ITEMS:", len(items))

        # ===== LOCATION =====
        try:
            page.locator("text=Select Location").click(timeout=5000)
        except:
            try:
                page.get_by_text("home", exact=True).click()
                print("Clicked Home")
            except:
                print("No location element")

        page.wait_for_timeout(2000)
        page.locator("//div[contains(text(),'Home')]").click()
        page.wait_for_timeout(2000)
        print("Location set")

        # ===== CLEAR CART =====
        try:
            cart_badge = page.locator("//span[@data-testid='cart-items-number']")

            if cart_badge.is_visible(timeout=3000):
                print("Clearing cart...")
                cart_badge.click()

                while True:
                    minus_btn = page.locator(
                        "(//button[contains(@aria-label, 'Remove') and contains(@data-testid, 'minus')])[1]"
                    )
                    try:
                        minus_btn.wait_for(state="visible", timeout=3000)
                        minus_btn.click()
                        page.wait_for_timeout(800)
                    except:
                        page.locator("//button[contains(@aria-label, 'Back Icon')]").click()
                        break
        except Exception as e:
            print("Cart skip:", e)

        # ===== ITEMS LOOP =====
        for idx, item_data in enumerate(items):

            print(f"\n===== ITEM {idx+1}/{len(items)} =====")

            try:
                item = item_data["name"]
                quantity = item_data["qty"]

                print(f"Adding {item} x{quantity}")

                # OPEN SEARCH
                page.get_by_test_id("searchBar").click()
                page.wait_for_timeout(1000)

                search_box = page.locator("//div//input[contains(@placeholder, 'Search')]")

                # CLEAR INPUT
                search_box.click()
                search_box.press("Control+A")
                search_box.press("Backspace")
                page.wait_for_timeout(500)

                # TYPE
                search_box.type(item, delay=120)
                search_box.press("Enter")

                print("Searching:", item)

                # WAIT RESULT
                page.wait_for_selector(
                    f'(//div/img[contains(translate(@title, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "{item.lower()}")])[1]',
                    timeout=10000
                )

                page.wait_for_timeout(2000)

                # ADD BUTTON
                add_button = page.locator(
                    f'(//div/img[contains(translate(@title, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "{item.lower()}")]//following-sibling::button[.="ADD"])[1]'
                )

                add_button.wait_for(state="visible", timeout=5000)
                add_button.scroll_into_view_if_needed()
                add_button.click()

                print("ADD clicked")

                page.wait_for_timeout(1500)

                # QUANTITY
                if quantity > 1:
                    plus_btn = page.locator("//button[contains(@aria-label, 'Increase quantity')]").first
                    plus_btn.wait_for(state="visible", timeout=5000)

                    for i in range(quantity - 1):
                        plus_btn.click()
                        page.wait_for_timeout(500)
                        print(f"+ clicked {i+1}")

                # 🔥 CRITICAL FIX: CLOSE SEARCH PANEL
                page.keyboard.press("Escape")
                page.wait_for_timeout(1000)

                print(f"✅ DONE {item}")

            except Exception as e:
                print(f"❌ ERROR on item {item_data}")
                traceback.print_exc()
                continue

        print("✅ ALL ITEMS ADDED")

        # ===== GO TO CART =====
        cart_btn_popup = page.locator("//div[contains(text(), 'Go to Cart')]")

        if cart_btn_popup.is_visible():
            cart_btn_popup.click()
        else:
            cart_btn = page.locator("//button[@data-testid='cart-btn']")
            cart_btn.wait_for(state="visible", timeout=5000)
            cart_btn.click(force=True)

        print("Cart opened")

        page.wait_for_timeout(2000)

        # ===== TOTAL =====
        total_locator = page.locator(
            "//span[contains(text(), 'Pay')]/parent::button/following-sibling::div//span[last()]"
        )

        total_locator.wait_for(state="visible")
        total_amount = total_locator.inner_text()

        print("TOTAL:", total_amount)

        return total_amount

    except Exception as e:
        print("❌ FATAL ERROR")
        traceback.print_exc()
        return "FAILED"

    finally:
        print("Closing browser safely...")
        try:
            if context:
                context.close()
        except:
            pass
        p.stop()

if __name__ == "__main__":
    import sys, json

    items = json.loads(sys.argv[1])
    user_id = sys.argv[2]

    print("Running automation...")
    run_zepto(items, user_id)