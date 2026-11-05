import React from 'react';
import { Link } from 'react-router-dom';
export const labels = {
    PENDING: 'Awaiting review',
    NEEDS_EVIDENCE: 'More evidence needed',
    CONFIRMED: 'Confirmed',
    REJECTED: 'Rejected',
    UNPAID: 'Payment pending',
    SANDBOX_PAID: 'Paid in sandbox',
    DISPUTED: 'Under dispute',
    VOID: 'Cancelled',
    APPROVED: 'Verified',
    LEGACY_UNVERIFIED: 'Historical record',
};
export const ruleName = (value) =>
    ({
        red_light: 'Red-light crossing',
        wrong_way: 'Wrong-way driving',
        restricted_zone: 'Restricted-zone entry',
        speeding: 'Speeding',
        no_parking: 'Prohibited parking',
        stop_line: 'Stop-line crossing',
    })[value] ||
    value ||
    'Traffic case';
export const money = (value) => '₹' + Number(value || 0).toLocaleString('en-IN');
export function Badge({ value }) {
    return (
        <span className={'status-tag status-' + String(value).toLowerCase()}>
            {labels[value] || value}
        </span>
    );
}
export function Origin({ item }) {
    return (
        <span className={'origin-tag ' + (item.is_demo ? 'demo' : 'recorded')}>
            {item.is_demo ? 'Demonstration' : 'Recorded case'} · {item.source_label}
        </span>
    );
}
export function PageHeader({ eyebrow, title, description, children }) {
    return (
        <header className="page-heading page-title">
            <div>
                <span className="eyebrow">{eyebrow}</span>
                <h1>{title}</h1>
                <p>{description}</p>
            </div>
            {children && <div className="heading-actions">{children}</div>}
        </header>
    );
}
export function Stats({ items }) {
    return (
        <div className="stat-grid">
            {items.map(([label, value, note, tone]) => (
                <article className={'stat-tile ' + (tone || '')} key={label}>
                    <span>{label}</span>
                    <strong>{value ?? '—'}</strong>
                    <small>{note}</small>
                </article>
            ))}
        </div>
    );
}
export function Workflow({ current = 0 }) {
    return (
        <ol className="workflow" aria-label="Case progress">
            {[
                'Evidence recorded',
                'RTO review',
                'Memo issued',
                'Payment or dispute',
            ].map((text, i) => (
                <li key={text} className={i <= current ? 'complete' : ''}>
                    <span>{i + 1}</span>
                    <div>{text}</div>
                </li>
            ))}
        </ol>
    );
}
export function HelpNote({ children }) {
    return (
        <div className="help-note">
            <span aria-hidden="true">i</span>
            <p>{children}</p>
        </div>
    );
}
export function CaseList({
    items = [],
    empty = 'There are no cases matching these filters.',
    government = false,
}) {
    return items.length ? (
        <div className="case-table-wrap">
            <table className="case-table">
                <thead>
                    <tr>
                        <th>Case & vehicle</th>
                        <th>Violation / location</th>
                        <th>Review</th>
                        <th>Memo</th>
                        <th>Next step</th>
                    </tr>
                </thead>
                <tbody>
                    {items.map((c) => (
                        <tr key={c.id}>
                            <td>
                                <Link className="case-ref" to={'/cases/' + c.id}>
                                    {c.reference}
                                </Link>
                                <strong>
                                    {government
                                        ? 'Vehicle identity restricted'
                                        : c.plate || 'Plate needs review'}
                                </strong>
                                <small>
                                    {government
                                        ? 'Government oversight'
                                        : c.vehicle?.owner_name ||
                                          'Owner not yet verified'}
                                </small>
                            </td>
                            <td>
                                <strong>{ruleName(c.type)}</strong>
                                <small>{c.location}</small>
                                <Origin item={c} />
                            </td>
                            <td>
                                <Badge value={c.status} />
                            </td>
                            <td>
                                {c.memo_status ? (
                                    <>
                                        <strong>{money(c.fine_amount)}</strong>
                                        <Badge value={c.memo_status} />
                                    </>
                                ) : (
                                    <small>Issued after confirmation</small>
                                )}
                            </td>
                            <td>
                                <Link to={'/cases/' + c.id}>
                                    {government ? 'View case summary' : c.next_action} →
                                </Link>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    ) : (
        <div className="empty-state">
            <div aria-hidden="true">✓</div>
            <h3>No cases here yet</h3>
            <p>{empty}</p>
        </div>
    );
}
export function ScopeControl({ value, onChange }) {
    return (
        <div className="scope-control" aria-label="Data source">
            {[
                ['all', 'All records'],
                ['demo', 'Demo examples'],
                ['live', 'Recorded cases'],
            ].map(([id, label]) => (
                <button
                    type="button"
                    key={id}
                    aria-pressed={value === id}
                    onClick={() => onChange(id)}
                >
                    {label}
                </button>
            ))}
        </div>
    );
}
