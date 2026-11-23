import React from 'react';
import { Link } from 'react-router-dom';
import { articlePath } from '../data/articles.js';

export default function ArticleCard({ article }) {
  return (
    <article className="news-article-card">
      <div className="news-article-image">
        <img src={article.image} alt={article.imageAlt ?? ''} loading="lazy" />
      </div>

      <div className="news-article-content">
        <div className="news-article-meta">
          <span className="listing-chip">{article.category}</span>
          <time dateTime={article.dateTime}>{article.date}</time>
        </div>
        <h3>{article.title}</h3>
        <p>{article.excerpt}</p>
        <Link className="home-button news-article-link" to={articlePath(article)} aria-label={`Read article: ${article.title}`}>
          Read article
          <img src="/assets/icons/home/arrow-text.svg" alt="" />
        </Link>
      </div>
    </article>
  );
}
