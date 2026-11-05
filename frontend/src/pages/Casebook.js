import React, { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useResource, Status, Pager } from '../components/WorkspaceUI';
import {
    PageHeader,
    CaseList,
    ScopeControl,
    HelpNote,
} from '../components/ExperienceUI';
export default function Casebook() {
    const { user } = useAuth();
    const [params, setParams] = useSearchParams();
    const [page, setPage] = useState(1);
    const [scope, setScope] = useState(
        ['all', 'demo', 'live'].includes(params.get('scope'))
            ? params.get('scope')
            : 'all',
    );
    const [q, setQ] = useState(params.get('q') || '');
    const status = params.get('status') || 'ALL';
    const resource = useResource(
        `/api/cases?page=${page}&scope=${scope}&status=${status}&q=${encodeURIComponent(q)}`,
        5000,
    );
    return (
        <div className="workspace">
            <PageHeader
                eyebrow={user.role === 'USER' ? 'MY CASES' : 'TRAFFIC CASE REGISTER'}
                title={
                    user.role === 'USER' ? 'Your case history' : 'Every case, connected'
                }
                description="Follow the evidence, review decision, memo and resolution without switching between disconnected records."
            />
            {user.role === 'GOVT' && (
                <HelpNote>
                    Government oversight shows case status and financial totals. Owner
                    identities, plates and evidence remain restricted to authorized RTO
                    staff.
                </HelpNote>
            )}
            <section className="panel">
                <div className="case-toolbar">
                    <label>
                        Search cases
                        <input
                            type="search"
                            value={q}
                            onChange={(e) => {
                                setQ(e.target.value);
                                setPage(1);
                            }}
                            placeholder={
                                user.role === 'GOVT'
                                    ? 'Case reference, location or violation'
                                    : 'Case reference, vehicle plate, location or violation'
                            }
                        />
                    </label>
                    <label>
                        Review status
                        <select
                            value={status}
                            onChange={(e) => {
                                setParams(
                                    e.target.value === 'ALL'
                                        ? {}
                                        : { status: e.target.value },
                                );
                                setPage(1);
                            }}
                        >
                            <option value="ALL">All statuses</option>
                            <option value="PENDING">Awaiting review</option>
                            <option value="NEEDS_EVIDENCE">More evidence needed</option>
                            <option value="CONFIRMED">Confirmed</option>
                            <option value="REJECTED">Rejected</option>
                        </select>
                    </label>
                    <ScopeControl
                        value={scope}
                        onChange={(s) => {
                            setScope(s);
                            setPage(1);
                        }}
                    />
                </div>
                <Status {...resource}>
                    <CaseList
                        items={resource.data?.items}
                        government={user.role === 'GOVT'}
                    />
                    <Pager page={page} setPage={setPage} total={resource.data?.total} />
                </Status>
            </section>
        </div>
    );
}
