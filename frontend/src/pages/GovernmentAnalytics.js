import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import {
    ResponsiveContainer,
    AreaChart,
    Area,
    XAxis,
    YAxis,
    Tooltip,
    CartesianGrid,
    PieChart,
    Pie,
    Cell,
} from 'recharts';
import { useResource, Status } from '../components/WorkspaceUI';
import {
    PageHeader,
    Stats,
    ScopeControl,
    CaseList,
    HelpNote,
    money,
    ruleName,
} from '../components/ExperienceUI';
export default function GovernmentAnalytics() {
    const [scope, setScope] = useState('all');
    const [from, setFrom] = useState('');
    const [to, setTo] = useState('');
    const [location, setLocation] = useState('');
    const [type, setType] = useState('');
    const options = useResource('/api/case-filters?scope=' + scope);
    const invalid = Boolean(from && to && from > to);
    const params = new URLSearchParams({ scope });
    if (from) params.set('from', new Date(from + 'T00:00:00+05:30').toISOString());
    if (to)
        params.set(
            'to',
            new Date(
                new Date(to + 'T00:00:00+05:30').getTime() + 86400000,
            ).toISOString(),
        );
    if (location) params.set('location', location);
    if (type) params.set('type', type);
    const resource = useResource(
        invalid ? null : '/api/overview?' + params.toString(),
        5000,
    );
    const data = resource.data;
    function clear() {
        setScope('all');
        setFrom('');
        setTo('');
        setLocation('');
        setType('');
    }

    return (
        <div className="workspace">
            <PageHeader
                eyebrow="GOVERNMENT OVERSIGHT"
                title="Government Analytics & Oversight"
                description="A shared view of case progress, workload and project memo totals. The same saved records power the RTO and citizen workflows."
            />
            <div className="panel analytics-filters">
                <ScopeControl
                    value={scope}
                    onChange={(value) => {
                        setScope(value);
                        setLocation('');
                        setType('');
                    }}
                />
                <label>
                    From (IST)
                    <input
                        type="date"
                        value={from}
                        onChange={(e) => setFrom(e.target.value)}
                    />
                </label>
                <label>
                    Through (IST)
                    <input
                        type="date"
                        value={to}
                        onChange={(e) => setTo(e.target.value)}
                    />
                </label>
                <label>
                    Location
                    <select
                        value={location}
                        onChange={(e) => setLocation(e.target.value)}
                    >
                        <option value="">All locations</option>
                        {options.data?.locations.map((x) => (
                            <option key={x}>{x}</option>
                        ))}
                    </select>
                </label>
                <label>
                    Violation type
                    <select value={type} onChange={(e) => setType(e.target.value)}>
                        <option value="">All types</option>
                        {options.data?.types.map((x) => (
                            <option value={x} key={x}>
                                {ruleName(x)}
                            </option>
                        ))}
                    </select>
                </label>
                <button onClick={clear}>Clear filters</button>
            </div>
            {invalid && (
                <p className="notice danger" role="alert">
                    The end date must be on or after the start date.
                </p>
            )}

            {!invalid && (
                <Status {...resource}>
                    <Stats
                        items={[
                            [
                                'Confirmed cases',
                                data?.confirmed,
                                'RTO-reviewed decisions',
                                'blue',
                            ],
                            [
                                'Awaiting review',
                                (data?.pending || 0) + (data?.needs_evidence || 0),
                                'Pending or missing evidence',
                                'amber',
                            ],
                            [
                                'Sandbox total',
                                money(data?.money.SANDBOX_PAID),
                                'Demonstration receipts only',
                                'green',
                            ],
                            [
                                'Open disputes',
                                data?.disputes,
                                'Cases needing resolution',
                                'red',
                            ],
                        ]}
                    />
                    <div className="two-columns analytics-grid">
                        <section className="panel">
                            <div className="section-heading">
                                <h2>Cases over time</h2>
                                <small>Daily · Asia/Kolkata filters</small>
                            </div>
                            <div className="chart-area">
                                {data?.trend.length ? (
                                    <ResponsiveContainer>
                                        <AreaChart data={data.trend}>
                                            <defs>
                                                <linearGradient
                                                    id="trend-fill"
                                                    x1="0"
                                                    y1="0"
                                                    x2="0"
                                                    y2="1"
                                                >
                                                    <stop
                                                        offset="0%"
                                                        stopColor="#2573b9"
                                                        stopOpacity={0.25}
                                                    />
                                                    <stop
                                                        offset="100%"
                                                        stopColor="#2573b9"
                                                        stopOpacity={0}
                                                    />
                                                </linearGradient>
                                            </defs>
                                            <CartesianGrid
                                                vertical={false}
                                                stroke="#edf0f3"
                                            />
                                            <XAxis
                                                dataKey="date"
                                                tick={{ fontSize: 11 }}
                                            />
                                            <YAxis
                                                allowDecimals={false}
                                                tick={{ fontSize: 11 }}
                                            />
                                            <Tooltip />
                                            <Area
                                                type="monotone"
                                                dataKey="cases"
                                                stroke="#2573b9"
                                                strokeWidth={3}
                                                fill="url(#trend-fill)"
                                            />
                                        </AreaChart>
                                    </ResponsiveContainer>
                                ) : (
                                    <p>No cases in this period.</p>
                                )}
                            </div>
                        </section>
                        <section className="panel">
                            <h2>Recorded violation types</h2>
                            <div className="chart-area chart-donut">
                                {data?.types.length > 0 && (
                                    <ResponsiveContainer>
                                        <PieChart>
                                            <Pie
                                                data={data.types}
                                                innerRadius={65}
                                                outerRadius={95}
                                                dataKey="value"
                                                paddingAngle={4}
                                            >
                                                {data.types.map((_, i) => (
                                                    <Cell
                                                        key={i}
                                                        fill={
                                                            [
                                                                '#2573b9',
                                                                '#2b9b7b',
                                                                '#e9ad49',
                                                                '#d96c61',
                                                                '#8b7bb0',
                                                            ][i % 5]
                                                        }
                                                    />
                                                ))}
                                            </Pie>
                                            <Tooltip />
                                        </PieChart>
                                    </ResponsiveContainer>
                                )}
                            </div>
                            <div className="chart-legend">
                                {data?.types.map((t, i) => (
                                    <span key={t.name}>
                                        <i
                                            style={{
                                                background: [
                                                    '#2573b9',
                                                    '#2b9b7b',
                                                    '#e9ad49',
                                                    '#d96c61',
                                                    '#8b7bb0',
                                                ][i % 5],
                                            }}
                                        />
                                        {ruleName(t.name)}
                                        <b>{t.value}</b>
                                    </span>
                                ))}
                            </div>
                        </section>
                    </div>
                    <div className="two-columns">
                        <section className="panel">
                            <h2>Cases by location</h2>
                            {data?.locations.map((l) => (
                                <div className="location-bar" key={l.name}>
                                    <div>
                                        <span>{l.name}</span>
                                        <b>{l.value}</b>
                                    </div>
                                    <meter
                                        value={l.value}
                                        min="0"
                                        max={Math.max(
                                            ...data.locations.map((x) => x.value),
                                            1,
                                        )}
                                    />
                                </div>
                            ))}
                        </section>
                        <section className="panel">
                            <h2>Memo status</h2>
                            <div className="amount-breakdown">
                                {[
                                    ['Outstanding', 'UNPAID'],
                                    ['Sandbox paid', 'SANDBOX_PAID'],
                                    ['Under dispute', 'DISPUTED'],
                                    ['Cancelled', 'VOID'],
                                ].map(([label, key]) => (
                                    <div key={key}>
                                        <span>{label}</span>
                                        <strong>{money(data?.money[key])}</strong>
                                    </div>
                                ))}
                            </div>
                            <HelpNote>
                                Sandbox receipts do not represent real government
                                revenue. Demo records can be separated using the source
                                selector above.
                            </HelpNote>
                        </section>
                    </div>
                    <section className="panel">
                        <div className="section-heading">
                            <h2>Recent case summaries</h2>
                            <Link to="/cases">Open case register →</Link>
                        </div>
                        <CaseList items={data?.recent} government />
                    </section>
                </Status>
            )}
        </div>
    );
}
