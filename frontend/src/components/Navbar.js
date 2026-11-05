import React from 'react';
import { Link, NavLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
export default function Navbar() {
    const { user, logout } = useAuth();
    if (!user)
        return (
            <nav className="public-nav">
                <Link to="/" className="brand">
                    <span>🚦</span>
                    <div>
                        e-Memo<small>Traffic management, connected</small>
                    </div>
                </Link>
                <span className="public-project-tag">Preksha · College project</span>
            </nav>
        );
    const staff = ['RTO', 'ADMIN'].includes(user.role);
    const links = staff
        ? [
              ['/rto', 'Overview', '▦'],
              ['/cases', 'Case register', '▤'],
              ['/operations', 'Reviews & requests', '✓'],
              ['/registry', 'Vehicles & owners', '▰'],
              ['/datasets', 'Dataset examples', '▧'],
              ['/monitor', 'Video analysis', '▷'],
              ['/calibration', 'Camera setup', '⌖'],
              ['/government', 'Analytics', '▥'],
          ]
        : user.role === 'GOVT'
          ? [
                ['/government', 'Overview & analytics', '▦'],
                ['/cases', 'Case oversight', '▤'],
            ]
          : [
                ['/dashboard', 'My dashboard', '▦'],
                ['/cases', 'My case history', '▤'],
            ];
    return (
        <aside className={'app-sidebar role-' + user.role.toLowerCase()}>
            <Link to="/" className="brand">
                <span>🚦</span>
                <div>
                    e-Memo<small>Traffic management</small>
                </div>
            </Link>
            <div className="portal-label">
                {user.role === 'USER'
                    ? 'VEHICLE OWNER'
                    : user.role === 'GOVT'
                      ? 'GOVERNMENT OVERSIGHT'
                      : user.role === 'ADMIN'
                        ? 'ADMINISTRATOR'
                        : 'RTO WORKSPACE'}
            </div>
            <nav aria-label="Workspace navigation">
                {links.map(([url, label, icon]) => (
                    <NavLink key={url} to={url} end>
                        <span aria-hidden="true">{icon}</span>
                        {label}
                    </NavLink>
                ))}
                {user.role === 'ADMIN' && (
                    <NavLink to="/admin">
                        <span aria-hidden="true">⚙</span>System management
                    </NavLink>
                )}
                <NavLink to="/guide">
                    <span aria-hidden="true">?</span>How to use this project
                </NavLink>
            </nav>
            <div className="sidebar-bottom">
                <div className="sidebar-avatar">{user.full_name.charAt(0)}</div>
                <div>
                    <Link to="/profile">{user.full_name}</Link>
                    <small>{user.role} account</small>
                </div>
                <button
                    aria-label="Logout"
                    onClick={async () => {
                        await logout();
                        window.location.assign('/');
                    }}
                >
                    ↗
                </button>
            </div>
        </aside>
    );
}
