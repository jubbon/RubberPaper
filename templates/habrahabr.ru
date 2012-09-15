{% extends "base.html" %}
{% block title %}
    <div align="center"><h1>habrahabr.ru</h1></div>
    <div align="center"><img src="http://habrahabr.ru/i/logo.gif"></div>
{% endblock title %}

{% block topic %}
    <div align="center"><h1><strong>{{ article.data.title }}</strong></h1></div>
    <br />
{% if article.data.original_author %}
    <div align="left">Автор: {{ article.data.original_author }}</div>
    <div align="left">Перевод: {{ article.author }}</div>
{% else %}
    <div align="left">Автор: {{ article.author }}</div>
{% endif %}
    <div align="left">Дата: {{ article.date }}</div>
    <div align="left">Ключевые слова: {{ article.data.keywords|join(", ") }}</div>
{% if article.data.hubs %}
    <div align="left">Хабы: {{ article.data.hubs|join(", ") }}</div>
{% endif %}
{% if article.data.hubs_prof %}
    <div align="left">Профильные хабы: {{ article.data.hubs_prof|join(", ") }}</div>
{% endif %}
    <br />
    <div align="justify">{{ article.data.content }}</div>
    <br />

{% if article.data.original_author %}
    <div align="right">Оригинал: <a href="{{ article.data.original_url }}">{{ article.data.original_url }}</a></div>
{% endif %}
    <div align="right"><a href="{{ article.url }}">{{ article.url }}</a></div>
{% endblock topic %}
