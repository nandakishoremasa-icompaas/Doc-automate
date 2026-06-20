import os
import sys
import shutil
import argparse
from playwright.sync_api import sync_playwright

def resolve_chrome_profile(selected_profile="Default"):
    sys_chrome_base = "/home/icsys-026/.config/google-chrome"
    local_profile_dir = "/home/icsys-026/policydocautomate/chrome_profile"

    # Only initialize if it doesn't exist to preserve manual logins
    if not os.path.exists(local_profile_dir):
        os.makedirs(local_profile_dir, exist_ok=True)
        dest_default = os.path.join(local_profile_dir, "Default")
        os.makedirs(dest_default, exist_ok=True)

        src_profile_dir = os.path.join(sys_chrome_base, selected_profile)
        if not os.path.exists(src_profile_dir):
            src_profile_dir = os.path.join(sys_chrome_base, "Default")

        # Copy Cookies
        src_c = os.path.join(src_profile_dir, "Cookies")
        dst_c = os.path.join(dest_default, "Cookies")
        if os.path.exists(src_c):
            shutil.copyfile(src_c, dst_c)
            print("✅ Copied cookies database.")

        # Copy Local State
        src_ls = os.path.join(sys_chrome_base, "Local State")
        dst_ls = os.path.join(local_profile_dir, "Local State")
        if os.path.exists(src_ls):
            shutil.copyfile(src_ls, dst_ls)
            print("✅ Copied Local State.")

    return local_profile_dir

def ensure_tabs_sidebar_open(page):
    treeitem_count = page.locator('div.chapter-item-label-and-buttons-container').count()
    if treeitem_count > 0:
        return True
    
    # Try finding the minimized switcher button
    show_btn = page.locator('[aria-label^="Show tabs and outlines"]').locator('visible=true').first
    if show_btn.count() > 0:
        print("Tabs sidebar seems collapsed. Clicking expand button...")
        show_btn.click(force=True)
        page.wait_for_timeout(3000)
        return True
        
    print("Warning: Could not verify if tabs sidebar is open.")
    return False

def dismiss_image_warning_if_present(page):
    try:
        # Check if the warning text or snackbar/butterbar is present
        # Using substring match for the text
        warning_text = page.locator('text=Images were not inserted').locator('visible=true')
        snackbar = page.locator('.appsElementsStackingSnackbarContainer, .appsElementsGm3WizSnackbar-snackbar, .docs-butterbar-container, .docs-butterbar, [class*="butterbar"], [class*="butterBar"], [class*="Snackbar"], [class*="snackbar"]').locator('visible=true')
        
        if warning_text.count() > 0 or snackbar.count() > 0:
            print("⚠️ 'Images were not inserted' warning or snackbar/butterbar detected. Dismissing...")
            
            # Find the container
            container = None
            if snackbar.count() > 0:
                container = snackbar.first
            elif warning_text.count() > 0:
                container = warning_text.first
            
            # Close button selectors
            close_selectors = [
                '[aria-label*="Close"]',
                '[aria-label*="Dismiss"]',
                '.docs-butterbar-close',
                '[class*="close"]',
                '[class*="dismiss"]',
                '[class*="action"]',
                'div[role="button"]',
                'span[role="button"]',
                'button',
                'text="✕"',
                'text="x"',
                'text="X"'
            ]
            
            dismissed = False
            if container:
                for selector in close_selectors:
                    btn = container.locator(selector).locator('visible=true').first
                    if btn.count() > 0 and btn.is_visible():
                        print(f"  Clicking close button in container using selector: {selector}")
                        btn.click(force=True)
                        page.wait_for_timeout(1000)
                        if warning_text.count() == 0 or not warning_text.first.is_visible():
                            dismissed = True
                            print("  ✅ Warning dismissed successfully!")
                            break
                            
            if not dismissed:
                # Try general selectors on the page
                for selector in close_selectors:
                    btn = page.locator(selector).locator('visible=true').first
                    if btn.count() > 0 and btn.is_visible():
                        print(f"  Clicking general close button using selector: {selector}")
                        btn.click(force=True)
                        page.wait_for_timeout(1000)
                        if warning_text.count() == 0 or not warning_text.first.is_visible():
                            dismissed = True
                            print("  ✅ Warning dismissed via general selector!")
                            break
            
            if not dismissed:
                print("  ⚠️ Standard close button click failed. Hiding via JS style.display...")
                # Fallback: Hide it using JS display = 'none'
                page.evaluate('''() => {
                    const elements = Array.from(document.querySelectorAll('*'));
                    for (const el of elements) {
                        if (el.textContent && el.textContent.includes("Images were not inserted")) {
                            let parent = el;
                            for (let i = 0; i < 5 && parent; i++) {
                                if (parent.classList.contains('docs-butterbar-container') || 
                                    parent.classList.contains('docs-butterbar') || 
                                    parent.id === 'docs-butterbar-container' ||
                                    parent.className.includes('butter') ||
                                    parent.className.includes('toast') ||
                                    parent.className.includes('notification') ||
                                    parent.className.includes('Snackbar') ||
                                    parent.className.includes('snackbar') ||
                                    parent.className.includes('SnackbarContainer')) {
                                    parent.style.display = 'none';
                                }
                                parent = parent.parentElement;
                            }
                            if (el.parentElement) {
                                el.parentElement.style.display = 'none';
                            }
                        }
                    }
                    const snackbars = document.querySelectorAll('.appsElementsStackingSnackbarContainer, .appsElementsGm3WizSnackbar-snackbar, .docs-butterbar-container, .docs-butterbar, [class*="butterbar"], [class*="butterBar"], [class*="Snackbar"], [class*="snackbar"]');
                    snackbars.forEach(s => s.style.display = 'none');
                }''')
                page.wait_for_timeout(1000)
                print("  ✅ Warning hidden via JS.")
    except Exception as e:
        print(f"Error while dismissing warning: {e}")

def check_editor_has_text(page):
    try:
        # Bypass Canvas virtualization by extracting text via memory clipboard
        # Crucial: Wipe the clipboard first to prevent Ghost Data from previous tabs
        page.evaluate("navigator.clipboard.writeText('')")
        page.wait_for_timeout(100)
        
        page.bring_to_front()
        page.evaluate("window.focus()")
        page.keyboard.press("Control+a")
        page.wait_for_timeout(100)
        page.keyboard.press("Control+c")
        page.wait_for_timeout(200)
        
        text = page.evaluate("navigator.clipboard.readText()")
        cleaned_text = text.strip().replace('\\n', '').replace('\\r', '').replace('\\t', '').replace('\\u200b', '')
        
        # Deselect text by clicking slightly off-center
        page.mouse.click(300, 300) 
        
        return len(cleaned_text) > 20
    except Exception as e:
        print(f"  ⚠️ Error checking editor content: {e}")
        return False

def scan_gdrive_folder(folder_url, target_url=None, profile="Default", verify_only=False, visible=False):
    # Ensure correct URL is used (fixes typo issue where 1 was used instead of l)
    folder_url = folder_url.replace("1ARO9HThbw1lCyCCC", "1ARO9HThbwl1CyCCC")
    
    local_profile_dir = resolve_chrome_profile(profile)

    mode_text = "visible mode" if visible else "invisible background mode"
    print(f"Launching Google Chrome Stable ({mode_text})...")
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            local_profile_dir,
            executable_path="/usr/bin/google-chrome",
            headless=not visible,
            viewport={"width": 1280, "height": 800},
            permissions=["clipboard-read", "clipboard-write"],
            ignore_default_args=["--password-store=basic", "--use-mock-keychain"],
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--no-first-run",
                "--no-default-browser-check",
                "--password-store=gnome-libsecret"
            ]
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.set_default_navigation_timeout(60000)
        page.set_default_timeout(60000)

        # 1. Open google.com first to initialize the session cookies securely
        print("Navigating to google.com to establish session...")
        page.goto("https://google.com")
        page.wait_for_timeout(5000)

        # 2. Open GDrive folder
        print(f"Navigating to folder: {folder_url}")
        page.goto(folder_url)
        page.wait_for_timeout(5000)
        
        # Save debug screenshot
        page.screenshot(path="scan_debug.png")

        print("Waiting for file list to load...")
        try:
            page.wait_for_selector("[role='row']", timeout=20000)
            print("Successfully loaded file list!")
        except Exception as e:
            print("❌ Failed to load file list. Please check the scan_debug.png screenshot to see the page state.")
            context.close()
            sys.exit(1)

        print("Scrolling to load all files...")
        files = {}
        prev_count = 0
        no_change = 0
        no_change_limit = 15

        try:
            for attempt in range(150):
                page.evaluate('''() => {
                    const scrollable = document.querySelector('c-wiz[scrollable="true"]');
                    if (scrollable) {
                        scrollable.focus();
                        scrollable.scrollTop += 600;
                    } else {
                        const elts = Array.from(document.querySelectorAll('*'));
                        const candidates = elts.filter(el => {
                            const style = window.getComputedStyle(el);
                            return (style.overflow === 'auto' || style.overflow === 'scroll' || 
                                    style.overflowY === 'auto' || style.overflowY === 'scroll') && 
                                   el.scrollHeight > el.clientHeight;
                        });
                        if (candidates.length > 0) {
                            candidates.sort((a, b) => b.scrollHeight - a.scrollHeight);
                            candidates[0].focus();
                            candidates[0].scrollTop += 600;
                        }
                    }
                }''')
                page.keyboard.press("PageDown")
                page.wait_for_timeout(1000)

                for row in page.locator("[role='row']").all():
                    try:
                        data_id = row.get_attribute("data-id")
                        if not data_id:
                            continue
                        text = row.inner_text().strip()
                        if not text:
                            continue
                        title = text.split("\n")[0].strip()
                        title = title.replace(".docx", "").replace(".doc", "").strip()
                        
                        # Smart Truncation: Google Docs limit is 50 characters. 
                        # We truncate to 45 to leave room for duplicate suffixes like " (2)".
                        if len(title) > 45:
                            title = title[:45].strip()
                        
                        if data_id not in files:
                            files[data_id] = title
                            print(f"  Found file #{len(files)}: {title}")
                    except Exception:
                        pass

                curr = len(files)
                if curr == prev_count:
                    no_change += 1
                else:
                    no_change = 0

                if no_change >= no_change_limit:
                    is_at_bottom = page.evaluate('''() => {
                        const scrollable = document.querySelector('c-wiz[scrollable="true"]');
                        if (scrollable) {
                            return (scrollable.scrollTop + scrollable.clientHeight >= scrollable.scrollHeight - 50);
                        }
                        return true;
                    }''')
                    if is_at_bottom:
                        break
                    else:
                        no_change = 0

                prev_count = curr

            print(f"\nScan complete! Total files found in source folder: {len(files)}")
        except Exception as e:
            print(f"\nScan interrupted or finished early! Total files found so far: {len(files)}")
            print("Reason:", e)

        source_page = None
        # Open target document/folder if provided
        if target_url:
            print(f"\nOpening Target URL: {target_url}")
            page.goto(target_url)
            page.wait_for_timeout(10000)
            print("Target URL opened successfully. Starting Tab verification/cleanup...")

            # 1. Sort the scanned files alphabetically to ensure strict order
            file_list = list(files.items())
            file_list.sort(key=lambda x: x[1].strip().lower())
            
            # Ensure outline/tabs sidebar is expanded
            ensure_tabs_sidebar_open(page)
            
            if verify_only:
                print("\n=======================================================")
                print("🚀 RUNNING IN STANDALONE VERIFICATION & HEALING MODE")
                print("=======================================================")
            else:
            
                # 2. Compare existing tabs with file list to find the first mismatch
                existing_tab_locs = page.locator('div.chapter-item-label-and-buttons-container')
                existing_tab_count = existing_tab_locs.count()
                existing_tabs = [existing_tab_locs.nth(j).inner_text().strip() for j in range(existing_tab_count)]
                
                mismatch_idx = len(file_list)
                for idx in range(min(len(file_list), len(existing_tabs))):
                    expected = file_list[idx][1].lower()
                    actual = existing_tabs[idx].lower()
                    
                    # Smart Match: Tolerate duplicate suffixes like "(2)" and truncation differences
                    if not (actual.startswith(expected) or expected.startswith(actual[:40])):
                        mismatch_idx = idx
                        break
                else:
                    if len(existing_tabs) < len(file_list):
                        mismatch_idx = len(existing_tabs)
                        
                print(f"Current tabs count in Google Doc: {existing_tab_count}")
                print(f"First mismatch index: {mismatch_idx} (Target Title: '{file_list[mismatch_idx][1]}' if index < {len(file_list)} else 'N/A')")
                
                # 3. Clean up any trailing mismatched/failed tabs
                target_count = max(1, mismatch_idx)
                if existing_tab_count > target_count:
                    print(f"Cleaning up {existing_tab_count - target_count} extra or mismatched tabs...")
                    while True:
                        current_tabs = page.locator('div.chapter-item-label-and-buttons-container')
                        count = current_tabs.count()
                        if count <= target_count:
                            break
                        print(f"Deleting tab #{count}: '{current_tabs.last.inner_text().strip()}'")
                        last_tab = current_tabs.last
                        last_tab.click(force=True)
                        page.wait_for_timeout(1000)
                        
                        last_tab.hover()
                        page.wait_for_timeout(500)
                        options_btn = last_tab.locator('[aria-label="Tab options"]')
                        options_btn.click(force=True)
                        page.wait_for_timeout(1000)
                        
                        delete_item = page.locator('div[role="menuitem"]:has-text("Delete")').locator('visible=true').first
                        delete_item.click(force=True)
                        page.wait_for_timeout(1000)
                        
                        confirm_btn = page.locator('button:has-text("Delete")').locator('visible=true').first
                        if confirm_btn.is_visible():
                            confirm_btn.click(force=True)
                        page.wait_for_timeout(2000)
                        
                # 4. Main loop will automatically handle renaming and clearing the root tab when i == 0.
                    
                # Force Google Docs to render all tabs by scrolling the sidebar before tracking names
                sidebar = page.locator('.navigation-widget-hats-container').first
                if sidebar.is_visible():
                    for _ in range(5):
                        sidebar.evaluate("el => el.scrollTop = el.scrollHeight")
                        page.wait_for_timeout(200)
                
                # Load existing active tab titles to track uniqueness
                current_tab_locs = page.locator('div.chapter-item-label-and-buttons-container')
                active_tab_titles = [current_tab_locs.nth(j).inner_text().strip() for j in range(current_tab_locs.count())]
                
                print(f"Resuming collation from index {mismatch_idx} ('{file_list[mismatch_idx][1]}')...")
                
                # Mismatch logic is already determined above.
                
                source_page = None
                for i in range(mismatch_idx, len(file_list)):
                    data_id, title = file_list[i]
                    
                    # Check uniqueness of tab title
                    unique_title = title
                    suffix = 2
                    while unique_title.lower() in [t.lower() for t in active_tab_titles]:
                        unique_title = f"{title} ({suffix})"
                        suffix += 1
                    
                    print(f"[{i+1}/{len(file_list)}] Setting up tab for: {unique_title}")
                    
                    # Check for and dismiss any persistent warning popup first
                    dismiss_image_warning_if_present(page)
                    
                    success = False
                    for attempt in range(1, 4):
                        try:
                            if i > 0:
                                # Add a new tab
                                add_btn = page.locator('[aria-label="Add tab"]')
                                add_btn.scroll_into_view_if_needed()
                                add_btn.click(force=True)
                                page.wait_for_timeout(100)
                                
                            # Rename active tab
                            active_tab = page.locator('div.chapter-item-label-and-buttons-container-selected')
                            active_tab.wait_for(state="visible", timeout=10000)
                            dismiss_image_warning_if_present(page)
                            active_tab.hover()
                            page.wait_for_timeout(100)
                            
                            options_btn = active_tab.locator('[aria-label="Tab options"]')
                            options_btn.click(force=True)
                            page.wait_for_timeout(100)
                            
                            rename_item = page.locator('div[role="menuitem"]:has-text("Rename")').locator('visible=true').first
                            rename_item.click(force=True)
                            
                            rename_input = active_tab.locator('input.goog-control')
                            rename_input.wait_for(state="visible", timeout=5000)
                            
                            for _ in range(10):
                                rename_input.fill(unique_title)
                                rename_input.press("Enter")
                                
                                # Autonomous Popup Resolution: Wait up to 1500ms for slow-animating popups
                                try:
                                    popup_ok_btn = page.locator('div[role="dialog"] button:has-text("OK")').locator('visible=true').first
                                    popup_ok_btn.wait_for(timeout=1500)
                                    print(f"  ⚠️ Name '{unique_title}' rejected by Google Docs popup. Auto-resolving...")
                                    popup_ok_btn.click(force=True)
                                    page.wait_for_timeout(500)
                                    suffix += 1
                                    unique_title = f"{title} ({suffix})"
                                    continue # Loop and try the new name
                                except Exception:
                                    # Timeout means the popup never appeared. Name was successfully accepted!
                                    break
                            
                            # Copy content from source document
                            file_url = f"https://docs.google.com/document/d/{data_id}/edit"
                            if source_page is None:
                                source_page = context.new_page()
                            
                            source_page.goto(file_url)
                            
                            print(f"  - Copying content from {unique_title}...")
                            source_page.bring_to_front()
                            source_page.evaluate("window.focus()")
                            source_page.wait_for_timeout(100)
    
                            editor = source_page.locator('.kix-appview-editor').first
                            editor.wait_for(state="visible", timeout=15000)
                            editor.click(force=True)
                            source_page.wait_for_timeout(500) # Must wait 500ms for Google Docs JS to focus caret
                            
                            source_page.keyboard.press("Control+a")
                            source_page.wait_for_timeout(300)
                            source_page.keyboard.press("Control+c")
                            source_page.wait_for_timeout(500)
                            
                            # Paste into target
                            print("  - Pasting into target tab...")
                            page.bring_to_front()
                            page.evaluate("window.focus()")
                            page.wait_for_timeout(100)
                            
                            target_editor = page.locator('.kix-appview-editor').first
                            target_editor.wait_for(state="visible", timeout=15000)
                            target_editor.click(force=True)
                            page.wait_for_timeout(500) # Must wait 500ms for Google Docs JS to focus caret
                            
                            # Canvas Wipe: Destroy any pre-existing text or failed paste artifacts
                            page.keyboard.press("Control+a")
                            page.wait_for_timeout(300)
                            page.keyboard.press("Backspace")
                            page.wait_for_timeout(300)
                            
                            # Clean Paste
                            page.keyboard.press("Control+v")
                            page.wait_for_timeout(1000) # Wait for paste buffer to flush
                            
                            # Verify the editor is not blank
                            if not check_editor_has_text(page):
                                print("  ⚠️ Verification failed: Editor appears to be blank. Retrying paste...")
                                raise Exception("Editor has no text content after paste.")
                                
                            dismiss_image_warning_if_present(page)
                            print(f"  ✅ Tab '{unique_title}' created, renamed, and content pasted!")
                            active_tab_titles.append(unique_title)
                            success = True
                            break
                        except Exception as e:
                            print(f"  ⚠️ Attempt {attempt} failed for {unique_title}: {e}")
                            if source_page:
                                try:
                                    source_page.close()
                                except Exception:
                                    pass
                                source_page = None
                            page.wait_for_timeout(2000)
                    
                    if not success:
                        print(f"❌ Failed to set up tab for {unique_title} after 3 attempts. Skipping to next document...")
                        if i > 0:
                            try:
                                print(f"  - Deleting failed tab: '{unique_title}'")
                                active_tab = page.locator('div.chapter-item-label-and-buttons-container-selected')
                                active_tab.hover()
                                page.wait_for_timeout(500)
                                options_btn = active_tab.locator('[aria-label="Tab options"]')
                                options_btn.click(force=True)
                                page.wait_for_timeout(1000)
                                
                                delete_item = page.locator('div[role="menuitem"]:has-text("Delete")').locator('visible=true').first
                                delete_item.click(force=True)
                                page.wait_for_timeout(1000)
                                
                                confirm_btn = page.locator('button:has-text("Delete")').locator('visible=true').first
                                if confirm_btn.is_visible():
                                    confirm_btn.click(force=True)
                                page.wait_for_timeout(2000)
                            except Exception as del_err:
                                print(f"  ⚠️ Could not delete failed tab: {del_err}")
                                
                        if source_page:
                            try:
                                source_page.close()
                            except Exception:
                                pass
                            source_page = None
    
            print(f"\n🎉 All {len(file_list)} files have been collated into their respective tabs!")
            
            # --- POST-COLLATION VERIFICATION PASS ---
            print("\n🔍 Initiating Post-Collation Verification Pass...")
            print("  - Scanning target document tabs to ensure data integrity...")
            try:
                page.bring_to_front()
                page.evaluate("window.focus()")
                page.wait_for_timeout(1000)
                
                tabs = page.locator('div.chapter-item-label-and-buttons-container')
                tab_count = tabs.count()
                print(f"  - Found {tab_count} total tabs in target document.")
                
                verification_errors = []
                
                for j in range(tab_count):
                    tab_el = tabs.nth(j)
                    tab_name = tab_el.inner_text().strip()
                    
                    if j >= len(file_list):
                        print(f"  ⚠️ Skipping unknown extra tab: '{tab_name}'")
                        continue
                        
                    expected_data_id, expected_title = file_list[j]
                    
                    print(f"[{j+1}/{len(file_list)}] Verifying tab: '{tab_name}' (Expected: '{expected_title}')...")
                    tab_el.scroll_into_view_if_needed()
                    tab_el.click(force=True)
                    page.wait_for_timeout(1500) # Give canvas time to load
                    
                    # 1. Name Healing
                    if tab_name.lower() in ["untitled tab", "new tab"] or (len(expected_title) > 5 and not tab_name.startswith(expected_title[:5])):
                        print(f"  🛠️ Self-Healing: Renaming '{tab_name}' to '{expected_title}'...")
                        try:
                            tab_el.hover()
                            page.wait_for_timeout(500)
                            options_btn = tab_el.locator('[aria-label="Tab options"]')
                            options_btn.click(force=True)
                            page.wait_for_timeout(500)
                            rename_item = page.locator('div[role="menuitem"]:has-text("Rename")').locator('visible=true').first
                            rename_item.click(force=True)
                            rename_input = tab_el.locator('input.goog-control')
                            rename_input.wait_for(state="visible", timeout=3000)
                            rename_input.fill(expected_title)
                            rename_input.press("Enter")
                            page.wait_for_timeout(1000)
                            print("  ✅ Rename Self-Healing Successful!")
                        except Exception as e:
                            print(f"  ⚠️ Rename Self-Healing failed: {e}")
                    
                    # 2. Data Healing
                    if not check_editor_has_text(page):
                        print(f"  ❌ Verification FAILED: Empty Canvas detected.")
                        print(f"  🛠️ Self-Healing: Re-copying data from source '{expected_title}'...")
                        try:
                            file_url = f"https://docs.google.com/document/d/{expected_data_id}/edit"
                            if source_page is None:
                                source_page = context.new_page()
                            source_page.goto(file_url)
                            source_page.bring_to_front()
                            source_page.evaluate("window.focus()")
                            source_page.wait_for_timeout(1000)
                            
                            editor = source_page.locator('.kix-appview-editor').first
                            editor.wait_for(state="visible", timeout=15000)
                            editor.click(force=True)
                            source_page.wait_for_timeout(500)
                            source_page.keyboard.press("Control+a")
                            source_page.wait_for_timeout(500)
                            source_page.keyboard.press("Control+c")
                            source_page.wait_for_timeout(1500)
                            
                            page.bring_to_front()
                            page.evaluate("window.focus()")
                            page.wait_for_timeout(500)
                            
                            target_editor = page.locator('.kix-appview-editor').first
                            target_editor.wait_for(state="visible", timeout=15000)
                            target_editor.click(force=True)
                            page.wait_for_timeout(500)
                            
                            # Canvas Wipe: Destroy any broken data or links before healing
                            page.keyboard.press("Control+a")
                            page.wait_for_timeout(500)
                            page.keyboard.press("Backspace")
                            page.wait_for_timeout(500)
                            
                            # Clean Paste
                            page.keyboard.press("Control+v")
                            page.wait_for_timeout(3000)
                            
                            if check_editor_has_text(page):
                                print("  ✅ Data Self-Healing Successful!")
                            else:
                                print("  ❌ Data Self-Healing Failed again.")
                                verification_errors.append(expected_title)
                        except Exception as e:
                            print(f"  ⚠️ Data Self-Healing encountered error: {e}")
                            verification_errors.append(expected_title)
                    else:
                        print(f"  ✅ Verification PASSED for tab: '{expected_title}' (Data Confirmed)")
                
                if verification_errors:
                    print(f"\n⚠️ Verification Complete with {len(verification_errors)} errors. Missing data in tabs: {', '.join(verification_errors)}")
                else:
                    print("\n🎉 Verification Complete: 100% Data Integrity Confirmed!")
            except Exception as v_err:
                print(f"  ⚠️ Verification process encountered an error: {v_err}")
            
        if source_page:
            try:
                source_page.close()
            except Exception:
                pass
        context.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, help="Google Drive folder URL")
    parser.add_argument("--target", required=False, help="Target Document or Folder URL")
    parser.add_argument("--profile", default="Default", help="Chrome profile name")
    parser.add_argument("--verify-only", action="store_true", help="Run only the verification pass")
    parser.add_argument("--visible", action="store_true", help="Run browser in visible mode for debugging")
    args = parser.parse_args()
    
    scan_gdrive_folder(args.source, args.target, args.profile, args.verify_only, args.visible)
