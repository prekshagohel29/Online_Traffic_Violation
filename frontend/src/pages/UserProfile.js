import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import './UserProfile.css';

const UserProfile = () => {
  const { user, updateProfile } = useAuth();
  const toast = useToast();
  
  const [fullName, setFullName] = useState(user?.full_name || '');
  const [phoneNumber, setPhoneNumber] = useState(user?.phone_number || '');
  const [password, setPassword] = useState('');
  const [currentPassword, setCurrentPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (password && password.length < 10) {
      toast.error("Password must be at least 10 characters");
      return;
    }

    setIsSubmitting(true);
    const updates = { full_name: fullName, phone_number: phoneNumber };
    if (password) { updates.password = password; updates.current_password = currentPassword; }

    const result = await updateProfile(updates);
    if (result.success) {
      toast.success("Profile updated successfully!");
      setPassword(''); // clear password field
    } else {
      toast.error(result.message);
    }
    setIsSubmitting(false);
  };

  return (
    <div className="profile-container">
      <div className="profile-card">
        <h2>My Profile</h2>
        <div className="profile-meta">
          <p><strong>Role:</strong> {user?.role}</p>
          <p><strong>Email:</strong> {user?.email}</p>
          <p><strong>Last Login:</strong> {user?.last_login ? new Date(user.last_login).toLocaleString() : 'First time login'}</p>
        </div>

        <form onSubmit={handleSubmit} className="profile-form">
          <div className="form-group">
            <label htmlFor="profile-full-name">Full Name</label>
            <input 
              type="text" id="profile-full-name"
              value={fullName} 
              onChange={(e) => setFullName(e.target.value)} 
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="profile-phone">Phone Number</label>
            <input 
              type="tel" id="profile-phone"
              value={phoneNumber} 
              onChange={(e) => setPhoneNumber(e.target.value)} 
              placeholder="+1 234 567 8900"
            />
          </div>
          <div className="form-group">
            <label htmlFor="profile-password">New Password (Leave blank to keep current)</label>
            <input 
              type="password" id="profile-password" autoComplete="new-password"
              value={password} 
              onChange={(e) => setPassword(e.target.value)} 
              placeholder="••••••••"
            />
          </div>
          <button type="submit" disabled={isSubmitting} className="save-btn">
            {isSubmitting ? 'Saving...' : 'Save Changes'}
          </button>
          {password && <label>Current password<input type="password" autoComplete="current-password" value={currentPassword} required onChange={e => setCurrentPassword(e.target.value)} /></label>}
        </form>
      </div>
    </div>
  );
};

export default UserProfile;
