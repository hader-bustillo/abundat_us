import json
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import logging
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('-l', '--log', required=False, help="Required: logging True or False", default="False")

args = parser.parse_args()

log = eval(args.log)

if log:
    # These two lines enable debugging at httplib level (requests->urllib3->http.client)
    # You will see the REQUEST, including HEADERS and DATA, and RESPONSE with HEADERS but without DATA.
    # The only thing missing will be the response.body which is not logged.
    try:
        import http.client as http_client
    except ImportError:
        # Python 2
        import httplib as http_client
    http_client.HTTPConnection.debuglevel = 1

    # You must initialize logging, otherwise you'll not see debug output.
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True


def main():
    user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
    headers = {

        "content-type": "application/json;charset=utf-8",

    }

    data = {
        "title": "Test post rest api without plugin",
        "content": "This is purely for testing rest api posting without any plugins. Post in draft status",
        "excerpt": "This is for testing",
        "slug": "Ledeaitest",
        "status": "draft"
    }

    username = "sports@homepagemediagroup.com"
    password = 'g6Mbpk*N(T4yN$*yM1(%PzH!'


    wp_urls = ['https://springhillhomepage.com/wp-json/wp/v2/posts',
              'https://brentwoodhomepage.com/wp-json/wp/v2/posts',
              'https://franklinhomepage.com/wp-json/wp/v2/posts',
              'https://nolensvillehomepage.com/wp-json/wp/v2/posts'
]

    wp_logon_urls = [
                    "https://springhillhomepage.com/wp-login.php",
                    "https://brentwoodhomepage.com/wp-login.php",
                    "https://franklinhomepage.com/wp-login.php",
                    "https://nolensvillehomepage.com/wp-login.php"
]

    for i in range(len(wp_urls)):
        wp_url = wp_urls[i]
        wp_logon_url = wp_logon_urls[i]
        try:
            chrome_options = webdriver.ChromeOptions()
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument("--remote-debugging-port=9222")
            chrome_options.add_argument('--headless')
            chrome_options.binary_location = '/usr/bin/google-chrome'

            driver = webdriver.Chrome(chrome_options=chrome_options)

            driver.get(wp_logon_url)
            # try:
            #     iframe = driver.find_element_by_xpath("//iframe[@src='about:blank']")
            #     driver.switch_to.frame(iframe)
            #     driver.find_element_by_class_name("no-thanks-wrapper").click()
            #     #handle pop up alerts
            #
            # except Exception:
            #     pass

            # find the required elements
            for i in range(3):
                driver.switch_to.default_content()
                user_login = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, 'user_login')))
                user_login.send_keys(username)
                time.sleep(3)
                user_pass = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, 'user_pass')))
                user_pass.clear()
                driver.execute_script("arguments[0].value = arguments[1]", user_pass, password)
                #        user_pass.send_keys(password)
                time.sleep(3)
                print("sent the user name and password\n")

                wp_submit = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, 'loginform')))
                print("found the wp-submit\n")
                wp_submit.submit()
                time.sleep(5)
                if 'ERROR' in driver.page_source:
                    continue
                else:
                    break

            print("executed the wp-submit\n")

            if 'wpApiSettings' in driver.page_source:
                resp = driver.execute_script("return wpApiSettings;")
                wp_nonce = resp['nonce']
            elif "data-nonce" in driver.page_source:
                resp = driver.page_source
                wp_nonce = resp.split("data-nonce=\"")[1].split('\"')[0]
            else:
                print("wp api settings not found")
                print(driver.page_source)
                raise
            wp_cookies = driver.get_cookies()
            driver.stop_client()
            driver.close()
        except Exception as e:
            print("login to the site failed\n")
            print(driver.page_source)
            driver.stop_client()
            driver.close()
            exit(1)

        with requests.Session() as s:
            s.cookies.clear()
            c = [s.cookies.set(c['name'], c['value']) for c in wp_cookies]

            headers['X-WP-Nonce'] = wp_nonce
            print("Testing a get post\n")
            get_resp = s.get(wp_url)
            if get_resp.status_code != 200:
                print("GET unsuccessful - status code %d\n", get_resp.status_code)
            else:
                print("GET successfull\n")
            print("posting through rest api")
            json_data = json.dumps(data)
            post_resp = s.post(wp_url, data=json_data, verify=False, headers=headers,allow_redirects=True)
            if post_resp.status_code != 201:
                print("POST unsuccessful - status code %d\n", post_resp.status_code)
            else:
                print("POST successfull\n")


if __name__ == '__main__':
    try:
        main()
    except ValueError as e:
        print(repr(e))