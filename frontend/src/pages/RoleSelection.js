import React from 'react';
import { useNavigate } from 'react-router-dom';
import './RoleSelection.css';

const RoleSelection = () => {
    const navigate = useNavigate();

    const handleSelect = (role) => {
        navigate(`/auth?role=${role}`);
    };

    return (
        <div className="role-selection-container">
            <div className="role-header">
                <h1>Welcome to e-Memo System</h1>
                <p>Please select your portal to continue</p>
            </div>

            <div className="role-cards">
                <button
                    type="button"
                    className="role-card user"
                    onClick={() => handleSelect('USER')}
                >
                    <div className="icon">👤</div>
                    <h2>Vehicle Owner</h2>
                    <p>
                        View your memos and evidence, request verified vehicle links,
                        and try sandbox payments.
                    </p>
                </button>

                <button
                    type="button"
                    className="role-card gov"
                    onClick={() => handleSelect('GOVT')}
                >
                    <div className="icon">🏛️</div>
                    <h2>Government</h2>
                    <p>
                        Explore aggregate traffic trends, confirmed events, pending
                        reviews and sandbox totals.
                    </p>
                </button>

                <button
                    type="button"
                    className="role-card admin"
                    onClick={() => handleSelect('RTO')}
                >
                    <div className="icon">🛂</div>
                    <h2>RTO Panel</h2>
                    <p>
                        Monitor video, calibrate cameras, review evidence and manage
                        project memos.
                    </p>
                </button>
                <button
                    type="button"
                    className="role-card admin"
                    onClick={() => handleSelect('ADMIN')}
                >
                    <div className="icon">⚙️</div>
                    <h2>Administrator</h2>
                    <p>
                        Manage trusted accounts, fine policies, audit records and
                        service readiness.
                    </p>
                </button>
            </div>
        </div>
    );
};

export default RoleSelection;
