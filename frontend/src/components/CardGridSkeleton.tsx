import './CardGridSkeleton.css';

export function CardGridSkeleton({ count = 15 }: { count?: number }) {
  return (
    <div className="grid skeleton-grid" aria-hidden="true">
      {Array.from({ length: count }, (_, i) => (
        <article key={i} className="card skeleton-card">
          <div className="skeleton-block skeleton-image" />
          <div className="card-body">
            <div className="skeleton-block skeleton-line short" />
            <div className="skeleton-block skeleton-line" />
            <div className="skeleton-block skeleton-line medium" />
            <div className="skeleton-block skeleton-line price" />
          </div>
        </article>
      ))}
    </div>
  );
}

export function ChangesSkeleton({ rows = 8 }: { rows?: number }) {
  return (
    <div className="changes-skeleton" aria-hidden="true">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="change-row skeleton-change-row">
          <div className="skeleton-block skeleton-line wide" />
          <div className="skeleton-block skeleton-line short" />
          <div className="skeleton-block skeleton-line tiny" />
        </div>
      ))}
    </div>
  );
}
