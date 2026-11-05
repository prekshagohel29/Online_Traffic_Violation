import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { http, errorMessage } from '../utils/api';
import { useResource, Status, Pager, MemoCard } from '../components/WorkspaceUI';
import { PageHeader, Stats, HelpNote, Badge, money } from '../components/ExperienceUI';
export default function UserDashboard() {
    const [page, setPage] = useState(1);
    const [q, setQ] = useState('');
    const [filter, setFilter] = useState('ALL');
    const memos = useResource(
        `/api/user/memos?page=${page}&status=${filter}&q=${encodeURIComponent(q)}`,
        5000,
    );
    const overview = useResource('/api/overview', 5000);
    const vehicles = useResource('/api/user/vehicles');
    const [linking, setLinking] = useState(false);
    const [plate, setPlate] = useState('');
    const [proof, setProof] = useState('');
    const [message, setMessage] = useState('');
    async function link(e) {
        e.preventDefault();
        try {
            await http.post('/api/user/vehicles/link', { plate, proof });
            setMessage(
                'Your request is with the RTO for verification. It will appear below.',
            );
            setPlate('');
            setProof('');
            setLinking(false);
            vehicles.reload();
        } catch (err) {
            setMessage(errorMessage(err));
        }
    }
    const data = overview.data;
    return (
        <div className="workspace">
            <PageHeader
                eyebrow="VEHICLE OWNER"
                title="My Vehicle Control Center"
                description="Your verified vehicles, case evidence and memos. Every action stays linked to its case."
            >
                <button onClick={() => setLinking(!linking)}>
                    + Request a vehicle link
                </button>
            </PageHeader>
            <Stats
                items={[
                    [
                        'Verified vehicles',
                        data?.vehicles,
                        'Only approved ownership links',
                        'blue',
                    ],
                    [
                        'To pay',
                        money(data?.money.UNPAID),
                        'Sandbox payments available',
                        'amber',
                    ],
                    [
                        'Sandbox paid',
                        money(data?.money.SANDBOX_PAID),
                        'Saved demonstration receipts',
                        'green',
                    ],
                    [
                        'Open disputes',
                        data?.disputes,
                        'Awaiting an RTO decision',
                        'red',
                    ],
                ]}
            />
            {message && (
                <p className="notice" role="status">
                    {message}
                </p>
            )}
            {linking && (
                <form className="panel form-grid" onSubmit={link}>
                    <div className="span-two">
                        <h2>Request vehicle ownership verification</h2>
                        <p>
                            The RTO checks your document reference before granting
                            access. Entering someone else’s plate gives no access to
                            their records.
                        </p>
                    </div>
                    <label>
                        Vehicle plate
                        <input
                            required
                            value={plate}
                            onChange={(e) => setPlate(e.target.value.toUpperCase())}
                            maxLength={25}
                        />
                    </label>
                    <label>
                        Ownership document reference
                        <textarea
                            required
                            value={proof}
                            onChange={(e) => setProof(e.target.value)}
                            placeholder="Registration certificate reference and how the RTO can verify it"
                            maxLength={2000}
                        />
                    </label>
                    <button>Send verification request</button>
                </form>
            )}
            <section className="panel">
                <div className="section-heading">
                    <h2>My vehicles</h2>
                    <small>Ownership is checked by the RTO</small>
                </div>
                <Status {...vehicles}>
                    <div className="owner-vehicle-grid">
                        {vehicles.data?.map((v) => (
                            <article key={v.id}>
                                <div className="vehicle-avatar">▰</div>
                                <div>
                                    <strong className="plate-number">{v.plate}</strong>
                                    <p>{v.vehicle_model || 'Linked vehicle'}</p>
                                    <Badge value={v.status} />
                                    {v.reason && <small>{v.reason}</small>}
                                </div>
                            </article>
                        ))}
                        {vehicles.data?.length === 0 && (
                            <p>No linked vehicles yet. Request a link to begin.</p>
                        )}
                    </div>
                </Status>
            </section>
            <div className="section-heading">
                <div>
                    <span className="eyebrow">WHAT NEEDS YOUR ATTENTION</span>
                    <h2>My memos</h2>
                </div>
                <Link to="/cases">Open complete case history →</Link>
            </div>
            <div className="case-toolbar">
                <label>
                    Search your memos
                    <input
                        type="search"
                        placeholder="Vehicle plate or violation"
                        value={q}
                        onChange={(e) => {
                            setQ(e.target.value);
                            setPage(1);
                        }}
                    />
                </label>
                <label>
                    Status
                    <select
                        value={filter}
                        onChange={(e) => {
                            setFilter(e.target.value);
                            setPage(1);
                        }}
                    >
                        <option value="ALL">All statuses</option>
                        <option value="UNPAID">Payment pending</option>
                        <option value="SANDBOX_PAID">Sandbox paid</option>
                        <option value="DISPUTED">Under dispute</option>
                        <option value="VOID">Cancelled</option>
                    </select>
                </label>
            </div>
            <Status {...memos}>
                {memos.data?.items
                    .filter((m) => filter === 'ALL' || m.status === filter)
                    .map((m) => (
                        <MemoCard
                            key={m.id}
                            memo={m}
                            citizen
                            reload={() => {
                                memos.reload();
                                overview.reload();
                            }}
                        />
                    ))}
                {!memos.data?.items.filter(
                    (m) => filter === 'ALL' || m.status === filter,
                ).length && (
                    <div className="panel empty-state">
                        <h3>No memos in this view</h3>
                        <p>
                            Try another filter or check whether your vehicle ownership
                            is approved.
                        </p>
                    </div>
                )}
                <Pager page={page} setPage={setPage} total={memos.data?.total} />
            </Status>
            <HelpNote>
                Payments in this college project are sandbox demonstrations. You can
                inspect the evidence, submit a dispute for an unpaid memo, or download a
                receipt. No real money is transferred.
            </HelpNote>
        </div>
    );
}
