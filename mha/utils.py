import re
import sys
import dateutil
import pprint
from datetime import datetime
from email.parser import HeaderParser


def dateParser(line):
    try:
        r = dateutil.parser.parse(line, fuzzy=True)

    # if the fuzzy parser failed to parse the line due to
    # incorrect timezone information issue #5 GitHub
    except ValueError:
        r = re.findall('^(.*?)\s*(?:\(|utc)', line, re.I)
        if r:
            r = dateutil.parser.parse(r[0])
    return r


def getHeaderVal(h, data, rex='\s*(.*?)\n\S+:\s'):
    r = re.findall('%s:%s' % (h, rex), data, re.X | re.DOTALL | re.I)
    if r:
        return r[0].strip()
    else:
        return None

def generate_report(header):
    r = {}
    n = HeaderParser().parsestr(header.strip())
    graph = []
    received = n.get_all('Received')
    if received:
        received = [i for i in received if ('from' in i or 'by' in i)]
    else:
        received = re.findall(
            'Received:\s*(.*?)\n\S+:\s+', mail_data, re.X | re.DOTALL | re.I)
    pprint.pprint(received)
    exit(1)
    c = len(received)
    for i in range(len(received)):
        if ';' in received[i]:
            line = received[i].split(';')
        else:
            line = received[i].split('\r\n')
        line = list(map(str.strip, line))
        line = [x.replace('\r\n', ' ') for x in line]
        try:
            if ';' in received[i + 1]:
                next_line = received[i + 1].split(';')
            else:
                next_line = received[i + 1].split('\r\n')
            next_line = list(map(str.strip, next_line))
            next_line = [x.replace('\r\n', '') for x in next_line]
        except IndexError:
            next_line = None

        org_time = dateParser(line[-1])
        if not next_line:
            next_time = org_time
        else:
            next_time = dateParser(next_line[-1])

        if line[0].startswith('from'):
            data = re.findall(
                """
                from\s+
                (.*?)\s+
                by(.*?)
                (?:
                    (?:with|via)
                    (.*?)
                    (?:\sid\s|$)
                    |\sid\s|$
                )""", line[0], re.DOTALL | re.X)
        else:
            data = re.findall(
                """
                ()by
                (.*?)
                (?:
                    (?:with|via)
                    (.*?)
                    (?:\sid\s|$)
                    |\sid\s
                )""", line[0], re.DOTALL | re.X)

        delay = (org_time - next_time).seconds
        if delay < 0:
            delay = 0

        try:
            ftime = org_time.utctimetuple()
            ftime = time.strftime('%m/%d/%Y %I:%M:%S %p', ftime)
            r[c] = {
                'Timestmp': org_time,
                'Time': ftime,
                'Delay': delay,
                'Direction': [x.replace('\n', ' ') for x in list(map(str.strip, data[0]))]
            }
            c -= 1
        except IndexError:
            pass

    for i in list(r.values()):
        if i['Direction'][0]:
            graph.append(["From: %s" % i['Direction'][0], i['Delay']])
        else:
            graph.append(["By: %s" % i['Direction'][1], i['Delay']])

    totalDelay = sum([x['Delay'] for x in list(r.values())])
    fTotalDelay = mha_tags.duration(totalDelay)
    delayed = True if totalDelay else False

    custom_style = Style(
        background='transparent',
        plot_background='transparent',
        font_family='googlefont:Open Sans',
        # title_font_size=12,
    )
    line_chart = pygal.HorizontalBar(
        style=custom_style, height=250, legend_at_bottom=True,
        tooltip_border_radius=10)
    line_chart.tooltip_fancy_mode = False
    line_chart.title = 'Total Delay is: %s' % fTotalDelay
    line_chart.x_title = 'Delay in seconds.'
    for i in graph:
        line_chart.add(i[0], i[1])
    chart = line_chart.render(is_unicode=True)

    summary = {
        'From': n.get('From') or getHeaderVal('from', mail_data),
        'To': n.get('to') or getHeaderVal('to', mail_data),
        'Cc': n.get('cc') or getHeaderVal('cc', mail_data),
        'Subject': n.get('Subject') or getHeaderVal('Subject', mail_data),
        'MessageID': n.get('Message-ID') or getHeaderVal('Message-ID', mail_data),
        'Date': n.get('Date') or getHeaderVal('Date', mail_data),
    }

    security_headers = ['Received-SPF', 'Authentication-Results',
                        'DKIM-Signature', 'ARC-Authentication-Results']
    context = {
        'data': r,
        'delayed': delayed,
        'summary': summary,
        'n': n,
        'chart': chart,
        'security_headers': security_headers
    }


if __name__ == "__main__":
    print(f'File: {sys.argv[1]}\n')
    with open(sys.argv[1], 'r') as f:
        report = generate_report(f.read())