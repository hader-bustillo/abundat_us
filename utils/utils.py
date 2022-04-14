import logging
import json
from datetime import datetime
from threading import Lock
import os
import boto3
from botocore.exceptions import ClientError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.utils import COMMASPACE, formatdate


logger = logging.getLogger(__name__)

send_mail_lock = Lock()


def properly_capitalize_team_name(team_name:str):
        if '-' in team_name:
            b = team_name.split("-")
            second = b[1].title()
            b[1] = second
            return "-".join(b)
        else:
            return team_name


def capitalize_acronyms(text: str):
    written_article = text
    vowel_list = ['a', 'e', 'i', 'o', 'u', 'A', 'E', 'I', 'O', 'U']
    first_word = written_article.split(' ', 1)[0]

    vowel_present = any(vowel in first_word for vowel in vowel_list)

    if not vowel_present and "'s" in first_word:
        wa = written_article.split(" ", 1)
        wa[0] = first_word.upper()
        wa[0] = wa[0].replace("'S","'s")
        written_article = ' '.join(wa)
    return written_article


def de_dup_list(d):
    out =  [i for n, i in enumerate(d) if i not in d[n + 1:]]
    return out


def remove_double_word(text:str):
    '''
    removes double words in sequence 'the the quick'
    '''
    a = text.split(' ')
    previous_word = ''
    current_word = ''
    for i in range(0,len(a)-2):
        logging.debug(i)
        if i < len(a): 
            current_word = a[i]
            if current_word.lower() == previous_word.lower():
                del a[i]
            else:
                previous_word = current_word
    return ' '.join(a)


def convert_to_title(s):
    if s is not None and type(s) is str: return s.title()
    else: return ''


def check_dict_for_empty_string(d:dict):
    for key in d.keys():
        if d[key] == '': d[key] = 'NONE_TEXT'
    return d


def replace_item_in_string(current:str,new,in_str:str):
    if current in in_str: return in_str.replace(current,str(new))
    else: return in_str


def get_random_int(top_amt): 
    import random
    return random.randint(a=0,b=top_amt)


def add_period_to_end(t:str):
    if len(t)>1:
        if t[-1] != '.':
            t = t + '.'
    return t


def convert_dict_to_str(d:dict):
    st = ''
    for key in d.keys():
        st = st + '%s - %i \n'%(key,d[key])
    return st


def convert_box_to_str(d:dict):
    st = ''
    for key in d.keys():
        try:
            st = st + '%s - %i          '%(key,d[key])
        except Exception as e:
            pass
    return st


def add_line_between_each_sentence(text:str):
    a = []
    c = True
    b = False
    for item in text.split():
        if b is True:
            if c is True:
                a.append('\n'+item)
                c = False
            else: 
                a.append('\n'+item)
            b = False
        elif item[-1] != '.':
            a.append(item)
        if item[-1] == '.' and item != 'St.':
            if item != 'U.':
                b = True
                a.append(item+'\n')
            
            
    h = " ".join(a)
    return h


def replace_items_for_mascot(text:str):
    if 'MASCOT' in text:
        text = replace_item_in_string(current='its ',in_str=text,new='their ')
        text = replace_item_in_string(current='was ',in_str=text,new='were ')
        text = replace_item_in_string(current=' it ',in_str=text,new=' they ')
        text = replace_item_in_string(current=' it were',in_str=text,new=' it was')
        text = replace_item_in_string(current=' It were',in_str=text,new=' It was')
        text = replace_item_in_string(current='There were no',in_str=text,new='There was no')
        
    return text


def get_item_from_list(l:list):
    return l[get_random_int(len(l)-1)]


def correct_articles_in_text(text: str):
    text_split = text.split()
    vowels = ['a','e','i','o','u','8','18','88']
    exceptions = ['honor', 'honorable']
    idx_for_an = []
    idx_for_a = []
    second_letter = ''
    for i in range(0,len(text_split)-1):
        if text_split[i].lower() == 'a' or text_split[i].lower() == 'an':
            if i+1 <= len(text_split)-1: 
                next_letter = text_split[i+1][0]
                if next_letter == '1': 
                    if len(text_split[i+1]) > 1:
                        second_letter = text_split[i+1][1]
                    if second_letter == '8': 
                        idx_for_an.append(i)
                if next_letter.lower() in vowels:
                    if text_split[i].lower() == 'a':
                        idx_for_an.append(i)
                if text_split[i+1].lower() in exceptions:
                    idx_for_an.append(i)
                        
    for i in range(0,len(text_split)-1):
        if i in idx_for_an:
            text_split[i] = 'an'
    return " ".join(text_split)


def capitalize_first_word_in_sentence(s:str):
    t = s.split()
    if len(t) > 0:
        if '[[' in t[0]: return s
        elif t[0][0].isupper(): return s
        else:
            up = t[0].capitalize()
            t[0] = up
            s = " ".join(t)
    return s


def get_scheduler_offset(general_config):

    if 'offset' in general_config:
        offset = general_config['offset']
    else:
        offset = 0
    return offset


def send_mail(send_from, send_to, subject, message, files=[]):
    """Compose and send email with provided info and attachments.

    Args:
        send_from (str): from name
        send_to (list[str]): to name
        subject (str): message title
        message (str): message body
        files (list[str]): list of file paths to be attached to email
        server (str): mail server host name
        port (int): port number
        username (str): server auth username
        password (str): server auth password
        use_tls (bool): use TLS mode
    """
    try:
        send_mail_lock.acquire()
        send_to = list(filter(None.__ne__, send_to))
        if send_from is None or send_to == []:
            return
        logging.info('Preparing export email to be sent...')
        import smtplib
        import os.path as op
        from email.mime.multipart import MIMEMultipart
        from email.mime.base import MIMEBase
        from email.mime.text import MIMEText
        from email.utils import COMMASPACE, formatdate
        from email import encoders

        server="smtp.office365.com"
        port=587
        username='staconsulting@outlook.com'
        password='tCz-XRC-QzZ-4d4'
        use_tls=True

        msg = MIMEMultipart()
        msg['From'] = send_from
        msg['To'] = COMMASPACE.join(send_to)
        msg['Date'] = formatdate(localtime=True)
        msg['Subject'] = subject

        msg.attach(MIMEText(message))

        for path in files:
            part = MIMEBase('application', "octet-stream")
            with open(path, 'r') as file:
                part.set_payload(file.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition',
                            'attachment; filename="{}"'.format(op.basename(path)))
            msg.attach(part)

        smtp = smtplib.SMTP(server, port)
        if use_tls:
            smtp.starttls()
        smtp.login(username, password)
        logging.info('Sending export email...')
        smtp.sendmail(send_from, send_to, msg.as_string())
        logging.info('Email sent!')
        smtp.quit()
    except Exception as e:
        logging.error("got an execption for email sending %s", repr(e))
        raise
    finally:
        send_mail_lock.release()
        logging.info("released sendmail lock")


def send_aws_email(send_from, send_to, subject, msg_txt='', msg_html='', files=[], filenames=[]):

    aws_region = "us-east-1"

    # The character encoding for the email.
    charset = "utf-8"

    # Create a new SES resource and specify a region.
    client = boto3.client('ses', region_name=aws_region)

    # Create a multipart/mixed parent container.
    msg = MIMEMultipart('mixed')
    # Add subject, from and to lines.
    msg['Subject'] = subject
    msg['From'] = send_from
    msg['To'] = COMMASPACE.join(send_to)

    # Create a multipart/alternative child container.
    msg_body = MIMEMultipart('alternative')

    # Encode the text and HTML content and set the character encoding. This step is
    # necessary if you're sending a message with characters outside the ASCII range.
    if msg_txt:
        textpart = MIMEText(msg_txt.encode(charset), 'plain', charset)
        msg_body.attach(textpart)
    if msg_html:
        htmlpart = MIMEText(msg_html.encode(charset), 'html', charset)
        msg_body.attach(htmlpart)

    # Attach the multipart/alternative child container to the multipart/mixed
    # parent container.
    msg.attach(msg_body)

    # The full path to the file that will be attached to the email.
    for file, filename in zip(files, filenames):
        # Define the attachment part and encode it using MIMEApplication.
        att = MIMEApplication(open(file, 'rb').read())

        # Add a header to tell the email client to treat this part as an attachment,
        # and to give the attachment a name.
        att.add_header('Content-Disposition', 'attachment', filename=filename)

        # Add the attachment to the parent container.
        msg.attach(att)
        # print(msg)
    try:
        # Provide the contents of the email.
        response = client.send_raw_email(
            Source=send_from,
            Destinations=send_to,
            RawMessage={
                'Data': msg.as_string()
            }
        )
    # Display an error if something goes wrong.
    except ClientError as e:
        logging.info(e.response['Error']['Message'])
        raise
    else:
        logging.info("Email sent! Message ID:%s", repr(response['MessageId']))


def get_log_level(general_config):
    try:
        log_level = getattr(logging, general_config['log_level'].upper())
    except (ValueError, KeyError):
        log_level = getattr(logging, "ERROR")
    return log_level

def get_apa_month_name(month: int):
    return apa_month_dict[month]


def get_apa_format_month(customer_config):
    apa_format_month = False

    if 'apa_format_month' in customer_config.general_config:
        apa_format_month = customer_config.general_config['apa_format_month']
    if hasattr(customer_config, 'apa_format_month'):
        apa_format_month = customer_config.apa_format_month
    return apa_format_month

day_of_week = {
    6: 'Sunday',
    0: 'Monday',
    1: 'Tuesday',
    2: 'Wednesday',
    3: 'Thursday',
    4: 'Friday',
    5: 'Saturday'
}

number_dict = {
    1: 'first',
    2: 'second',
    3: 'third',
    4: 'fourth',
    5: 'fifth',
    6: 'sixth',
    7: 'seventh',
    8: 'eighth',
    9: 'ninth',
    10: 'tenth',
    11: 'eleventh',
    12: 'twelfth',
    13: 'thirteenth',
    14: 'fourteenth',
    15: 'fifteenth',
    16: 'sixteenth',
    17: 'seventeenth',
    18: 'eighteenth',
    19: 'nineteenth',
    20: 'twentieth',
    21: 'twenty-first',
    22: 'twenty-second',
    23: 'twenty-third',
    24: 'twenty-fourth',
    25: 'twenty-fifth',
    26: 'twenty-sixth',
    27: 'twenty-seventh',
    28: 'twenty-eighth',
    29: 'twenty-ninth',
    30: 'thirtieth'
    
}

month_dict = {
    1: 'January',
    2: 'February',
    3: 'March',
    4: 'April',
    5: 'May',
    6: 'June',
    7: 'July',
    8: 'August',
    9: 'September',
    10: 'October',
    11: 'November',
    12: 'December'
    
}

apa_month_dict = {
    1: 'Jan.',
    2: 'Feb.',
    3: 'March',
    4: 'April',
    5: 'May',
    6: 'June',
    7: 'July',
    8: 'Aug.',
    9: 'Sept.',
    10: 'Oct.',
    11: 'Nov.',
    12: 'Dec.'
}

state_dict = {
        'AK': 'Alaska',
        'AL': 'Alabama',
        'AR': 'Arkansas',
        'AS': 'American Samoa',
        'AZ': 'Arizona',
        'CA': 'California',
        'CO': 'Colorado',
        'CT': 'Connecticut',
        'DC': 'District of Columbia',
        'DE': 'Delaware',
        'FL': 'Florida',
        'GA': 'Georgia',
        'GU': 'Guam',
        'HI': 'Hawaii',
        'IA': 'Iowa',
        'ID': 'Idaho',
        'IL': 'Illinois',
        'IN': 'Indiana',
        'KS': 'Kansas',
        'KY': 'Kentucky',
        'LA': 'Louisiana',
        'MA': 'Massachusetts',
        'MD': 'Maryland',
        'ME': 'Maine',
        'MI': 'Michigan',
        'MN': 'Minnesota',
        'MO': 'Missouri',
        'MP': 'Northern Mariana Islands',
        'MS': 'Mississippi',
        'MT': 'Montana',
        'NA': 'National',
        'NC': 'North Carolina',
        'ND': 'North Dakota',
        'NE': 'Nebraska',
        'NH': 'New Hampshire',
        'NJ': 'New Jersey',
        'NM': 'New Mexico',
        'NV': 'Nevada',
        'NY': 'New York',
        'OH': 'Ohio',
        'OK': 'Oklahoma',
        'OR': 'Oregon',
        'PA': 'Pennsylvania',
        'PR': 'Puerto Rico',
        'RI': 'Rhode Island',
        'SC': 'South Carolina',
        'SD': 'South Dakota',
        'TN': 'Tennessee',
        'TX': 'Texas',
        'UT': 'Utah',
        'VA': 'Virginia',
        'VI': 'Virgin Islands',
        'VT': 'Vermont',
        'WA': 'Washington',
        'WI': 'Wisconsin',
        'WV': 'West Virginia',
        'WY': 'Wyoming'
}
