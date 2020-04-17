import logging
from bs4 import BeautifulSoup
import time
import urllib.request
import calendar
import dateutil.parser
from dateutil import tz
from spontit import SpontitResource

TIME_INTERVAL_TO_CHECK = 30  # 30 seconds
UPDATE_TIME_FILE = "last_update.txt"
ENCODING = "utf8"
PARSER = "html.parser"
TIME_ZONE_538 = "America/New_York"

# Replace with your userId and channelId.
# To get more info, run help(SpontitResource)
# or check out the docs: https://github.com/spontit/spontit-api-python-wrapper
SPONTIT_USER_ID = "liveupdates"
SPONTIT_CHANNEL_TO_UPDATE = "liveupdates/538updates"
SPONTIT_SECRET_KEY = None


def get_html_str_from_url(url_to_retrieve, wait_to_open=False):
    """
    Gets the HTML from the URL passed.
    :param url_to_retrieve: The URL to download
    :param wait_to_open: Whether or not to wait for some of the Javascript to load items in the HTML before pulling it
    :return: A string representing the HTML
    """
    # noinspection PyBroadException
    try:
        fp = urllib.request.urlopen(url_to_retrieve)
    except Exception:
        return False
    if wait_to_open:
        time.sleep(10)
    my_bytes = fp.read()
    html_str = my_bytes.decode(ENCODING)
    fp.close()
    return html_str


def get_section_from_html(html_str, container_type_str, container_attributes):
    """
    Gets a particular section from the HTML string.
    :param html_str: The HTML string downloaded
    :param container_type_str: The container type
    :param container_attributes: The container attributes used to locate the container
    :return: The container found
    """
    soup = BeautifulSoup(html_str, features="html.parser")
    return soup.find(container_type_str, container_attributes)


def get_538_trump_approval():
    """
    Gets the newest 538 approval/disapproval estimates for the most addicted gamblers.
    If there is a new update, send a push notification.
    :return: -
    """
    # Get the HTML from the 538 website.
    html_str = get_html_str_from_url("https://projects.fivethirtyeight.com/trump-approval-ratings",
                                     wait_to_open=False)
    html_str = str(html_str)
    time_stamp_p_str = get_section_from_html(str(html_str), "p", {"class": "timestamp"}).string

    # noinspection PyBroadException
    try:
        time_stamp_p_str = time_stamp_p_str[7:].strip()
    except Exception:
        print("Failed at parsing.")
        return

    # Get the time stamp of when the website was last updated.
    from_zone = tz.gettz(TIME_ZONE_538)
    to_zone = tz.gettz('UTC')
    date_538_last_updated = dateutil.parser.parse(time_stamp_p_str)
    utc = date_538_last_updated.replace(tzinfo=from_zone)
    utc_time_str = utc.astimezone(to_zone)
    epoch_time_stamp_538_last_updated = calendar.timegm(utc_time_str.timetuple())

    # Get the most recent approval and disapproval ratings.
    d4 = utc_time_str.strftime("%Y-%m-%d")
    approve_front_to_split = f'"date":"{d4}","future":false,"subgroup":"All polls","approve_estimate":"'
    approve_end_to_split = '","approve_hi":"'
    disapprove_front_to_split = '","disapprove_estimate":"'
    disapprove_end_to_split = '","disapprove_hi":"'
    first_approve_str = html_str.split(approve_front_to_split)[1]
    approve = first_approve_str.split(approve_end_to_split)[0]
    disapprove_str = first_approve_str.split(disapprove_front_to_split)[1]
    disapprove = disapprove_str.split(disapprove_end_to_split)[0]

    # Construct the alert to send.
    alert = "NEW Trump Approval Ratings:\nApprove: " + str(round(float(approve), 2)) \
            + "%\nDisapprove: " + str(round(float(disapprove), 2)) + "%"

    # Get the time last updated.
    try:
        f = open(UPDATE_TIME_FILE, "r")
        last = f.read()
        last_updated = int(last)
    except FileNotFoundError:
        last_updated = 0

    # If an update is needed, send an update.
    # Determine if an update is needed by comparing the most recent update time on 538's website with our local record
    # of the last time we updated.
    if last_updated < epoch_time_stamp_538_last_updated:
        if SPONTIT_SECRET_KEY is None:
            raise Exception("You must fill out your secret key at the top of the file. You can get a secret key and "
                            "push for FREE at spontit.com/secret_keys.")
        resource = SpontitResource(SPONTIT_USER_ID, SPONTIT_SECRET_KEY)
        resource.push(alert, channel_id=SPONTIT_CHANNEL_TO_UPDATE)

        # Write the new most recent update time.
        f = open(UPDATE_TIME_FILE, "w")
        f.write(str(int(time.time())))
        f.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format='[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s')

    while True:

        logging.info("------ SERVER AWAKENED -----")
        # noinspection PyBroadException
        try:
            get_538_trump_approval()
        except Exception as e:
            print("538 ERROR")
            print(e)
        logging.info("------ SERVER SLEEPING -----")

        time.sleep(TIME_INTERVAL_TO_CHECK)
