import type { TokenContribution } from "../api";

type ContributionChartProps = {
  contributions: TokenContribution[];
  title?: string;
};

export function ContributionChart({
  contributions,
  title = "Top evidence tokens",
}: ContributionChartProps) {
  if (!contributions.length) return null;

  const maxAbs = Math.max(
    ...contributions.map((c) => Math.abs(c.contribution)),
    1e-9,
  );

  return (
    <div className="explain">
      <p className="explain__title">{title}</p>
      <ul className="explain__list">
        {contributions.map((c) => {
          const width = (Math.abs(c.contribution) / maxAbs) * 100;
          const positive = c.contribution >= 0;
          return (
            <li key={`${c.token}-${c.contribution}`} className="explain__row">
              <span className="explain__token">{c.token}</span>
              <div className="explain__track">
                <span
                  className={`explain__bar ${positive ? "explain__bar--pos" : "explain__bar--neg"}`}
                  style={{ width: `${width}%` }}
                />
              </div>
              <span className="explain__value">
                {positive ? "+" : ""}
                {c.contribution.toFixed(3)}
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
