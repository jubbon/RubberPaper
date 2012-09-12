#!/usr/bin/python
# -*- coding: utf-8 -*-

DEFAULT_TIMEZONE = "Europe/Moscow"

import re
import urllib2
import urlparse

from bs4 import BeautifulSoup

def parse_article(url):
    try:
        response = urllib2.urlopen(url)
        data = response.read()
    except:
        raise urllib2.URLError('Failed to download')
    soup = BeautifulSoup(data)

    # Metadata
    post_div = soup.find('div', 'post')

    # Хабы
    raw_hubs = post_div.find('div', 'hubs')
    hubs = []
    hubs_prof = []

    for child in raw_hubs.find_all(True):
        if child.name == 'a':
            hubs.append(child.text.strip())
        elif child.name == 'span':
            hubs_prof.append(hubs.pop())

    # Заголовок статьи
    title = post_div.find('span', 'post_title').text.strip()

    # Ключевые слова
    keywords = [a.text.strip() for a in post_div.find('ul', 'tags').find_all('a', rel='tag')]

    infopanel = post_div.find('div', 'infopanel')

    # Автор статьи
    author = infopanel.find('div', 'author').a.text.strip()

    # Дата публикации
    published = infopanel.find('div', 'published').text.strip()

    # Текст статьи
    content = post_div.find('div', 'content')
    content.find('div', 'clear').decompose()

    # Комментарии
    comments = [parse_comment(comment) for comment in soup.find_all('div', 'comment_item')]

    article = {
        'url': url,
        'title': title,
        'author':author,
        'date': published,
        'hubs': hubs,
        'hubs_prof': hubs_prof,
        'keywords': keywords,
        'content': content,
        'comments': comments,
    }
    #article.update(footer)
    return article



def parse_footer(infopanel):
    score = infopanel.find('span', 'score')
    score_up, score_down, score_total = parse_score(score)

    raw_author = infopanel.find('div', 'author')
    author = raw_author.a.text.strip()
    author_rating = raw_author.span.text.strip()

    footer = {
        'score_up': score_up,
        'score_down': score_down,
        'score_total': score_total,
        'favs_count': infopanel.find('div', 'favs_count').text.strip(),
        'author': author,
        'author_rating': author_rating
    }

    return footer

def parse_comment(comment_div):
    author_banned = comment_div.find('div', 'author_banned')
    if author_banned is not None:
        comment = {
            'banned': True,
            'content': unicode(author_banned),
            'comment_id': comment_div['id'][8:], # 'comment_NNN'
            'parent_id': None if comment_div.parent['class'] != 'reply_comments' else
                         comment_div.parent['id'][15:], # reply_comments_NNN
        }

        return comment

    score = comment_div.find('span', 'score')
    score_up, score_down, score_total = parse_score(score)

    comment_id = comment_div.find('a', 'link_to_comment')['href'][9:]

    to_parent = comment_div.find('a', 'to_parent')
    parent_id = to_parent['data-parent_id'] if (to_parent is not None
                    and to_parent['data-parent_id'] != comment_id) else None

    comment = {
        'banned': False,
        'score_up': score_up,
        'score_down': score_down,
        'score_total': score_total,
        'author': comment_div.find('a', 'username').text.strip(),
        'published': comment_div.find('time').text.strip(),
        'comment_id': comment_id,
        'parent_id': parent_id,
        'content': comment_div.find('div', 'message')
    }

    return comment

def parse_score(score):
    try:
        title = score['title']
        rating_up, rating_down = re.findall('\d+', title)[1:]
        rating_total = score.text.strip()
        return rating_up, rating_down, rating_total
    except ValueError: # voting time is not over yet
        return '???', '???', '???'

import os.path
import dateutil.parser
from dateutil.parser import parserinfo

def render(hostname, topics, output):
    ''' Save articles in document
    '''
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader('templates'))
    tmpl = env.get_template(hostname)
    import ho.pisa as pisa
    pisa.showLogging()

    import tempfile
    articles = list()
    for topic in topics:
        try:
            content = tmpl.render(articles = (topic,))
            with tempfile.TemporaryFile('wb') as temp:
                pisa.CreatePDF(content.encode('utf-8'), temp)
            articles.append(topic)
        except Exception, exc:
            print "ERROR!!!", exc

    content = tmpl.render(articles = articles)
    pisa.CreatePDF(content.encode('utf-8'), output)


def main():
    try:
        import argparse
        parser = argparse.ArgumentParser(description = "RubberPaper")
        parser.add_argument("-v", "--verbose", metavar = "verbose", help = "Verbose output")
        subparser = parser.add_subparsers(dest="command", help = "commands")

        feed_parser = subparser.add_parser("feed", help = "Collect one or more feeds")
        feed_parser.add_argument('--url')

        render_parser = subparser.add_parser("render", help = "Render a PDF document")
        render_parser.add_argument('--date')
        render_parser.add_argument('--output', type = argparse.FileType("wb"))
        render_parser.add_argument('--url')

        convert_parser = subparser.add_parser("convert", help = "Convert a storage")
        convert_parser.add_argument('--input', required = True)
        convert_parser.add_argument('--output', required = True)

        try:
            args = parser.parse_args()
        except IOError, err:
            parser.error(str(err))

        import shelve
        from contextlib import closing

        if args.command == "feed":
            ''' Обработка фидов
            '''
            dateparser = dateutil.parser.parser()
            if args.url:
                feeds = (args.url, )
            else:
                feeds = (
                        "http://habrahabr.ru/rss",
                        "http://habrahabr.ru/rss/corporative",
                        "http://habrahabr.ru/rss/blogs/python",
                        "http://habrahabr.ru/rss/blogs/django",
                        "http://habrahabr.ru/rss/blogs/cpp",
                        "http://habrahabr.ru/rss/blogs/qt_software",
                        "http://habrahabr.ru/rss/blogs/programming",
                        "http://habrahabr.ru/rss/blogs/algorithm",
                        "http://habrahabr.ru/rss/blogs/nix_coding",
                        "http://habrahabr.ru/rss/blogs/git",
                        "http://habrahabr.ru/rss/blogs/complete_code",
                        "http://habrahabr.ru/rss/blogs/refactoring",
                        "http://habrahabr.ru/rss/blogs/system_development",
                        "http://habrahabr.ru/rss/blogs/iconoskaz",
                        "http://habrahabr.ru/rss/blogs/open_source",
                        "http://habrahabr.ru/rss/blogs/development",
                        "http://habrahabr.ru/rss/blogs/development_tools",
                        "http://habrahabr.ru/rss/blog/html5",
                        "http://habrahabr.ru/rss/blogs/cuda",
                        "http://habrahabr.ru/rss/blogs/xml",
                        "http://habrahabr.ru/rss/blogs/code_review",
                        "http://habrahabr.ru/rss/blogs/regex",
                        "http://habrahabr.ru/rss/blogs/vs",
                        "http://habrahabr.ru/rss/blog/cloud_computing",
                        "http://habrahabr.ru/rss/blog/hi",
                        "http://habrahabr.ru/rss/blogs/books",
                        "http://habrahabr.ru/rss/blogs/ebooks",
                        "http://habrahabr.ru/rss/blogs/hpodcasts",
                        "http://habrahabr.ru/rss/blogs/it_bigraphy",
                        "http://habrahabr.ru/rss/blogs/history",
                        "http://habrahabr.ru/rss/blogs/gtd",
                        "http://habrahabr.ru/rss/blogs/study",
                        "http://habrahabr.ru/rss/company/pocketbook/blog",
                        "http://habrahabr.ru/rss/company/microsoft/blog",
                        "http://habrahabr.ru/rss/company/yandex/blog",
                        "http://habrahabr.ru/rss/blogs/startup",
                        "http://habrahabr.ru/rss/blogs/firefox",
                        "http://habrahabr.ru/rss/blogs/yandex",
                        "http://habrahabr.ru/rss/blogs/google",
                        "http://habrahabr.ru/rss/blogs/internet",
                        "http://habrahabr.ru/rss/blogs/testing",
                        "http://habrahabr.ru/rss/blogs/tdd",
                        "http://habrahabr.ru/rss/blogs/agile",
                        "http://habrahabr.ru/rss/blogs/pm",
                        "http://habrahabr.ru/rss/blogs/conference",
                        "http://habrahabr.ru/rss/blogs/hr",
                        "http://habrahabr.ru/rss/blogs/office",
                        "http://habrahabr.ru/rss/blogs/infosecurity",
                        "http://habrahabr.ru/rss/blogs/virus",
                        "http://habrahabr.ru/rss/blogs/web_security",
                        "http://habrahabr.ru/rss/blogs/crypto",
                        "http://habrahabr.ru/rss/blogs/sysadm",
                        "http://habrahabr.ru/rss/blogs/virtualization",
                        "http://habrahabr.ru/rss/blogs/network_technologies",
                        "http://habrahabr.ru/rss/blogs/sql",
                        "http://habrahabr.ru/rss/blogs/memcached",
                        "http://habrahabr.ru/rss/blogs/postgresql",
                        "http://habrahabr.ru/rss/blogs/mongodb",
                        "http://habrahabr.ru/rss/blogs/nosql",
                        "http://habrahabr.ru/rss/blogs/linux",
                        "http://habrahabr.ru/rss/blogs/ubuntu",
                        "http://habrahabr.ru/rss/blogs/windows",
                        "http://habrahabr.ru/rss/blogs/android",
                        "http://habrahabr.ru/rss/blogs/nix",
                        )

            import feedparser
            for feed in feeds:
                print "Processing feed {0}...".format(feed)
                index_file_name = os.path.expanduser(os.path.join("~", ".rubber", "index", urlparse.urlsplit(feed).hostname))
                with closing(shelve.open(index_file_name, flag="w")) as storage:
                    news = feedparser.parse(feed)
                    for n in reversed(news.entries):
                        # Ссылка на новость
                        url = n.link.encode("utf-8")
                        if not storage.has_key(url):
                            article = dict()

                            # Ссылка на статью
                            article["url"] = url.encode("utf-8")
                            print "URL:{0}".format(article["url"]).strip()

                            # Заголовок новости
                            article["title"] = n.title.encode("utf-8")
                            print "Title:{0}".format(article["title"]).strip()

                            # Дата опубликования новости
                            article["date"] = dateparser.parse(n.published)
                            print "Date:{0}".format(article["date"]).strip()

                            # Автор новости
                            if hasattr(n, "author"):
                                article["author"] = n.author.encode("utf-8")
                                print "Author:{0}".format(article["author"]).strip()

                            storage[url] = article
        elif args.command == "render":
            ''' Генерация PDF-файла
            '''
            import datetime
            from dateutil.relativedelta import relativedelta, MO
            import pytz
            kword = "today"
            offset = None
            d = re.compile("^(\w+)(?:-(\d+))?$")
            if args.date:
                m = d.match(args.date)
                if m:
                    kword = m.group(1)
                    offset = m.group(2)
                    if offset: offset = int(offset)
                else:
                    print "Неверный формат опции"

            today = datetime.date.today()
            if kword == "today":
                date_after = today
                if offset: date_after = date_after + relativedelta(days=-offset)
                date_before = date_after + relativedelta(days=+1)
            elif kword == "yesterday":
                date_before = today
                if offset: date_before = date_before + relativedelta(days=-offset)
                date_after = date_before + relativedelta(days=-1)
            elif kword == "week":
                date_after = today + relativedelta(weekday=MO(-1))
                if offset: date_after = date_after + relativedelta(weeks=-offset)
                date_before = date_after + relativedelta(weeks=+1)
            elif kword == "month":
                date_after = today + relativedelta(day=1)
                if offset: date_after = date_after + relativedelta(months=-offset)
                date_before = date_after + relativedelta(months=+1)
            elif kword == "year":
                date_after = today + relativedelta(month=1, day=1)
                if offset: date_after = date_after + relativedelta(years=-offset)
                date_before = date_after + relativedelta(years=+1)

            tz = pytz.timezone(DEFAULT_TIMEZONE)
            date_after = datetime.datetime.combine(date_after, datetime.time(tzinfo = tz))
            if args.verbose: print date_after
            date_before = datetime.datetime.combine(date_before, datetime.time(tzinfo = tz))
            if args.verbose: print date_before

            if args.output:
                topics = list()
                if args.url:
                    hostname = urlparse.urlsplit(args.url).hostname
                    if urlparse.urlsplit(args.url).path in ("", "/"):
                        index_file_name = os.path.expanduser(os.path.join("~", ".rubber", "index", urlparse.urlsplit(args.url).hostname))
                        with closing(shelve.open(index_file_name, flag="r")) as storage:
                            for topicid in storage.keys():
                                topic = storage[topicid]
                                date = topic["date"]
                                if date >= date_after and date < date_before:
                                    topic["data"] = parse_article(topic["url"])
                                    topics.append(topic)
                    else:
                        urls = (args.url, )
                else:
                    for dirpath, dirnames, filenames in os.walk(os.path.expanduser(os.path.join("~", ".rubber", "index"))):
                        for filename in filenames:
                            if filename in ("habrahabr.ru",):
                                index_file_name = os.path.join(dirpath, filename)
                                with closing(shelve.open(index_file_name, flag="r")) as storage:
                                    for topicid in storage.keys():
                                        topic = storage[topicid]
                                        date = topic["date"]
                                        if date >= date_after and date < date_before:
                                            topic["data"] = parse_article(topic["url"])
                                            topics.append(topic)
                # Generating document
                render(hostname, topics, args.output)
        elif args.command == "convert":
            ''' Преобразование хранилища
            '''
            topics = list()
            with closing(shelve.open(os.path.expanduser(args.output), flag="c")) as out_storage:
                with closing(shelve.open(os.path.expanduser(args.input), flag="r")) as in_storage:
                    for topicid in in_storage.keys():
                        topic = in_storage[topicid]
                        for value in topic.keys():
                            if isinstance(topic[value], str):
                                print "Converting {0}".format(topic[value])
                                topic[value] = topic[value].decode("utf-8")
                        out_storage[topicid] = topic
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
