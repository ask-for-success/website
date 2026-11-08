import React from 'react';
import { Link } from 'react-router-dom';

export default function ArticleCard({ article }) {
  return (
    <article className="content-card article-card">
      <div className={`article-art ${article.tone}`} aria-hidden="true">
        <span>{article.category}</span>
      </div>
      <div className="article-content">
        <p className="card-kicker">{article.date}</p>
        <h3>{article.title}</h3>
        <p className="card-copy">{article.excerpt}</p>
        <Link className="text-link" to="/news">Read story <span aria-hidden="true">→</span></Link>
      </div>
    </article>
  );
}
