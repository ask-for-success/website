import React from 'react';
import ArticleCard from '../components/ArticleCard.jsx';
import SectionTitle from '../components/SectionTitle.jsx';
import articles from '../data/articles.js';

export default function News() {
  return (
    <section className="section container page-section">
      <SectionTitle eyebrow="News & stories" title="Good things are happening here" description="Updates, ideas, and stories from people making a difference in our community." />
      <div className="card-grid">
        {articles.map((article) => <ArticleCard key={article.id} article={article} />)}
      </div>
    </section>
  );
}
