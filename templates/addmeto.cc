{% extends "base.html" %}
{% block title %}
    <div align="center"><h1>Бобук - Еще один линкблог</h1></div>
{% endblock title %}

{% block topic %}
    <div align="center"><h1>{{ article.title }}</h1></div>
	<div align="left">Дата: {{ article.date }}</div>
    <div align="justify">{{ article.summary }}</div>
    <br />
    <div align="right"><a href="{{ article.url }}">{{ article.url }}</a></div>
{% endblock topic %}