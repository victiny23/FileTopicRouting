import type { Role } from "../api";

type AppHeaderProps = {
  role: Role;
  onRoleChange: (role: Role) => void;
  tau: number;
  defaultTau: number;
  onTauChange: (tau: number) => void;
  onTauReset: () => void;
  tauDisabled: boolean;
};

export function AppHeader({
  role,
  onRoleChange,
  tau,
  defaultTau,
  onTauChange,
  onTauReset,
  tauDisabled,
}: AppHeaderProps) {
  return (
    <header className="topbar">
      <div className="topbar__brand">
        <span className="topbar__mark" aria-hidden="true" />
        <div>
          <p className="topbar__title">Doc Center Router</p>
          <p className="topbar__subtitle">Topic routing with human review</p>
        </div>
      </div>

      <div className="topbar__controls">
        <div className="role-switch" role="group" aria-label="User role">
          <button
            type="button"
            className={`role-switch__btn${role === "user" ? " is-active" : ""}`}
            onClick={() => onRoleChange("user")}
          >
            User
          </button>
          <button
            type="button"
            className={`role-switch__btn${role === "reviewer" ? " is-active" : ""}`}
            onClick={() => onRoleChange("reviewer")}
          >
            Reviewer
          </button>
        </div>

        {role === "reviewer" ? (
          <div className="tau-control">
            <label className="tau-control__label" htmlFor="tau-slider">
              Max-proba threshold
              <span className="tau-control__value">{tau.toFixed(2)}</span>
            </label>
            <input
              id="tau-slider"
              className="tau-control__slider"
              type="range"
              min={0.15}
              max={0.85}
              step={0.01}
              value={tau}
              disabled={tauDisabled}
              onChange={(e) => onTauChange(Number(e.target.value))}
            />
            <button
              type="button"
              className="tau-control__reset"
              disabled={tauDisabled || Math.abs(tau - defaultTau) < 0.001}
              onClick={onTauReset}
            >
              Reset to {defaultTau.toFixed(2)}
            </button>
          </div>
        ) : null}
      </div>
    </header>
  );
}
