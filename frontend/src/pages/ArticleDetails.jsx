import React, { Fragment } from 'react';
import { useParams } from 'react-router-dom';
import ArticleCard from '../components/ArticleCard.jsx';
import { DetailBackLink, DetailMeta, DetailNotFound } from '../components/DetailNavigation.jsx';
import articles, { featuredArticle, getArticle } from '../data/articles.js';

function ArticleBody({ sections }) {
  return (
    <div className="article-detail-body detail-prose">
      {sections.map(({ heading, paragraphs, quote, quoteAuthor, figure, continuation }) => (
        <Fragment key={heading}>
          <section className="detail-section">
            <h2>{heading}</h2>
            {paragraphs.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}
          </section>
          {quote && (
            <figure className="article-detail-quote">
              <blockquote><p>{quote}</p></blockquote>
              <figcaption>{quoteAuthor}</figcaption>
            </figure>
          )}
          {figure && (
            <figure className="article-detail-figure">
              <img src={figure.image} alt={figure.alt} loading="lazy" />
              <figcaption>{figure.caption}</figcaption>
            </figure>
          )}
          {continuation && <p>{continuation}</p>}
        </Fragment>
      ))}
    </div>
  );
}

export default function ArticleDetails() {
  const { slug } = useParams();
  const article = getArticle(slug);

  if (!article) {
    return <DetailNotFound title="Article not found" description="This story could not be found. Browse News for available stories." backTo="/news" backLabel="Back to news" />;
  }

  const related = article === featuredArticle
    ? articles.slice(0, 3)
    : articles.filter((other) => other.category === article.category && other.slug !== slug);

  return (
    <article className="site-shell detail-page article-detail">
      <header className="detail-header">
        <div className="article-detail-header">
          <DetailBackLink to="/news">Back to news</DetailBackLink>
          <div className="detail-title">
            <span className="listing-chip">{article.category}</span>
            <h1>{article.title}</h1>
            <p>{article.excerpt}</p>
          </div>
          <div className="article-detail-byline">
            {article.author && (
              <div className="article-detail-author">
                {article.authorImage && <img src={article.authorImage} alt="" width="48" height="48" />}
                <div>
                  <p>{article.author}</p>
                  <small>{article.authorRole}</small>
                </div>
              </div>
            )}
            <div className="detail-meta">
              <DetailMeta icon="calendar"><time dateTime={article.dateTime}>{article.date}</time></DetailMeta>
              {article.readTime && <DetailMeta icon="clock">{article.readTime}</DetailMeta>}
            </div>
          </div>
        </div>
        <img className="detail-cover article-detail-cover" src={article.image} alt={article.imageAlt} fetchPriority="high" />
      </header>

      {article.body ? <ArticleBody sections={article.body} /> : (
        <section className="detail-section detail-content-note">
          <h2>Full article unavailable</h2>
          <p>Only the preview above is available for this story.</p>
        </section>
      )}

      {related.length > 0 && (
        <section className="detail-related" aria-labelledby="more-stories-title">
          <header className="listing-section-title">
            <h2 id="more-stories-title">More stories</h2>
            <p>Recaps, announcements and stories.</p>
          </header>
          <div className="news-article-grid">
            {related.map((story) => <ArticleCard key={story.slug} article={story} />)}
          </div>
        </section>
      )}
    </article>
  );
}
