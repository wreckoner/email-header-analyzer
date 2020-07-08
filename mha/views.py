from django.shortcuts import render
from django.views.generic import TemplateView
from django.utils import dateparse

from email.parser import HeaderParser
import time
import dateutil.parser

from datetime import datetime
import re

import pygal
from pygal.style import Style

import geoip2.database

from .templatetags import mha_tags
from .utils import dateParser, getHeaderVal

import pprint




class IndexView(TemplateView):
    http_method_names = ['get', 'post']
    template_name = "mha_index.html"

    def post(self, request, *args, **kwargs):
        mail_data = request.POST['headers'].strip() 
        r = {}
        parsed_headers = HeaderParser().parsestr(mail_data)
        parsed_headers_dict = {}
        major_header_names = {'From', 'Message-Id', 'Date', 'Subject', 'To', 'Cc'}
        major_headers = {}
        x_headers = {}
        security_header_names = {'Received-SPF', 'Authentication-Results', 'DKIM-Signature', 'ARC-Authentication-Results'}
        security_headers = {}
        other_headers = {}
        for header in parsed_headers:
            parsed_headers_dict[header.replace('-', '_')] = parsed_headers.get(header)
            if header in major_header_names:
                major_headers[header] = parsed_headers.get(header)
            elif header.startswith('X-'):
                x_headers[header] = parsed_headers.get(header)
            elif header in security_header_names:
                security_headers[header] = parsed_headers.get(header)
            else:
                other_headers[header] = parsed_headers.get(header)
        
        graph = []
        received = parsed_headers.get_all('Received')
        if received:
            received = [i for i in received if ('from' in i or 'by' in i)]
        else:
            received = re.findall(
                'Received:\s*(.*?)\n\S+:\s+', mail_data, re.X | re.DOTALL | re.I)
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

        
        context = {
            'hops': sorted(list(r.items()), key=lambda x: x[0]),
            'delayed': delayed,
            'n': parsed_headers,
            'chart': chart,
            'headers': parsed_headers_dict,
            'major_headers': major_headers,
            'x_headers': x_headers,
            'security_headers': security_headers,
            'other_headers': other_headers
        }
        return render(request, self.template_name, context=context)