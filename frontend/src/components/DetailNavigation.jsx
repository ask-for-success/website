import React from 'react';
import { Link } from 'react-router-dom';

export function DetailBackLink({ to, children }) {
  return (
    <Link className="detail-back-link" to={to}>
      <img src="/assets/icons/details/back.svg" alt="" width="20" height="20" />
      {children}
    </Link>
  );
}

export function DetailMeta({ icon, children }) {
  return (
    <span className="detail-meta-item">
      <img src={`/assets/icons/details/${icon}.svg`} alt="" width="20" height="20" />
      {children}
    </span>
  );
}

export function DetailNotFound({ title, description, backTo, backLabel }) {
  return (
    <section className="site-shell detail-page detail-not-found">
      <DetailBackLink to={backTo}>{backLabel}</DetailBackLink>
      <h1>{title}</h1>
      <p>{description}</p>
    </section>
  );
}
