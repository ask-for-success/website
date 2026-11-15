import React from 'react';
import { ArrowRight } from 'lucide-react';

export default function ArticleCard({ article }) {
  return (
    <article className="news-article-card">
      <div className="news-article-image" aria-hidden="true">
        <img src={article.image} alt="" loading="lazy" />
      </div>

      <div className="news-article-content">
        <div className="news-article-meta">
          <span className="news-article-category">{article.category}</span>
          <time dateTime={article.dateTime}>{article.date}</time>
        </div>
        <h3>{article.title}</h3>
        <p>{article.excerpt}</p>
        <a className="news-article-link" href="#featured-story">
          Read article <ArrowRight size={15} aria-hidden="true" />
        </a>
      </div>
    </article>
  );
}
