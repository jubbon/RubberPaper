#!/usr/bin/python
# -*- coding: utf-8 -*-

DEFAULT_TIMEZONE = "Europe/Moscow"

import re
import os.path
import urllib2
import urlparse
import datetime
import pytz
import dateutil.parser
from dateutil.parser import parserinfo
from bs4 import BeautifulSoup


class HabraHabrRu:
    url = "habrahabr.ru"
    def parse(cls, data):
        article = dict()
        soup = BeautifulSoup(data)

        # Metadata
        post_div = soup.find('div', 'post')
        if post_div is None:
            # Статья отсутствует
            return None

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

        # Автор и адрес оригинальной статьи
        try:
            article["original_author"] = infopanel.find('div', 'original-author').a.text.strip()
            print "Original author: {0}".format(article["original_author"])
            article["original_url"] = infopanel.find('div', 'original-author').a["href"].strip()
            print "Original url: {0}".format(article["original_url"])
        except:
            pass

        # Автор статьи или перевода
        author = infopanel.find('div', 'author').a.text.strip()

        # Дата публикации
        published = infopanel.find('div', 'published').text.strip()

        # Текст статьи
        content = post_div.find('div', 'content')
        content.find('div', 'clear').decompose()

        # Комментарии
        comments = [parse_comment(comment) for comment in soup.find_all('div', 'comment_item')]

        article.update({
            'title': title,
            'author':author,
            'date': published,
            'hubs': hubs,
            'hubs_prof': hubs_prof,
            'keywords': keywords,
            'content': content,
            'comments': comments,
        })
        return article


class PyPi:
    url = "pypi.python.org"
    def parse(cls, data):
        article = dict()
        soup = BeautifulSoup(data)

        # Текст статьи
        content = soup.find('div', 'section')
        print str(content)
        content.h1.decompose()
        #content.h1.replace("h2")
        if content.find('table', 'list'):
            content.find('table', 'list').decompose()
        article["content"] = content

        return article


def parse_article(url):
    article = None
    try:
        hostname = urlparse.urlsplit(url).hostname
        response = urllib2.urlopen(url)
        data = response.read()
        if hostname == "habrahabr.ru":
            article = HabraHabrRu().parse(data)
        elif hostname == "pypi.python.org":
            article = PyPi().parse(data)
    except:
        return None
        #raise urllib2.URLError('Failed to download')
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
        feed_parser.add_argument('--name')

        render_parser = subparser.add_parser("render", help = "Render a PDF document")
        render_parser.add_argument('--date')
        render_parser.add_argument('--output', type = argparse.FileType("wb", 0))
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
            feeds = list()
            if args.url:
                feeds.append(args.url)
            elif args.name:
                feed_list_filename = os.path.expanduser(os.path.join("~", ".rubber", "feed-lists", args.name))
                with open(feed_list_filename, "rt") as f:
                    for feed in f:
                        feeds.append(feed.strip())
            else:
                for dirpath, dirnames, filenames in os.walk(os.path.expanduser(os.path.join("~", ".rubber", "feed-lists"))):
                    for filename in filenames:
                        feed_list_filename = os.path.join(dirpath, filename)
                        with open(feed_list_filename, "rt") as f:
                            for feed in f:
                                feeds.append(feed.strip())

            import feedparser
            for feed in feeds:
                try:
                    print "Processing feed {0}...".format(feed)
                    index_file_name = os.path.expanduser(os.path.join("~", ".rubber", "index", urlparse.urlsplit(feed).hostname))
                    with closing(shelve.open(index_file_name, flag = "c")) as storage:
                        news = feedparser.parse(feed)
                        # Кодировка сообщений
                        codepage = news.encoding
                        for n in reversed(news.entries):

                            # Ссылка на новость
                            url = n.link
                            # Идентификатор новости
                            if hasattr(n, "id"):
                                topicid = n.id
                            else:
                                topicid = url

                            if not storage.has_key(topicid.encode("utf-8")):
                                article = dict()

                                # Ссылка на статью
                                article["url"] = url
                                print "URL:{0}".format(article["url"].encode("utf-8")).strip()

                                # Заголовок новости
                                article["title"] = n.title
                                print "Title:{0}".format(article["title"].encode("utf-8")).strip()

                                # Дата опубликования новости
                                article["date"] = None
                                if hasattr(n, "published"):
                                    article["date"] = dateparser.parse(n.published)
                                elif hasattr(n, "updated"):
                                    article["date"] = dateparser.parse(n.updated)
                                else:
                                    article["date"] = datetime.datetime.now(pytz.timezone(DEFAULT_TIMEZONE))
                                if article["date"]:
                                    print "Date:{0}".format(article["date"]).strip()

                                # Автор новости
                                if hasattr(n, "author"):
                                    article["author"] = n.author
                                    print "Author:{0}".format(article["author"].encode("utf-8")).strip()

                                # Содержание новости
                                if hasattr(n, "summary"):
                                    article["summary"] = n.summary

                                storage[topicid.encode("utf-8")] = article
                except Exception, exc:
                    print exc
        elif args.command == "render":
            ''' Генерация PDF-файла
            '''
            from dateutil.relativedelta import relativedelta, MO
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
