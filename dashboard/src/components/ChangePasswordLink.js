import React, { useState } from 'react';
import { FiKey, FiX } from 'react-icons/fi';
import { authAPI } from '../services/api';

// "Change Password" row for the sidebars. Accounts are created by an
// administrator, so the first password is one somebody else chose; a change
// signs out every other session, and this browser keeps working with the
// fresh tokens the server returns.
export default function ChangePasswordLink({ rowStyle, iconStyle }) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ current: '', next: '', confirm: '' });
  const [errors, setErrors] = useState({});
  const [saving, setSaving] = useState(false);
  const [done, setDone] = useState(false);

  const close = () => {
    setOpen(false);
    setForm({ current: '', next: '', confirm: '' });
    setErrors({});
    setDone(false);
  };

  const submit = async (e) => {
    e.preventDefault();
    if (form.next !== form.confirm) {
      setErrors({ confirm: 'The new passwords do not match.' });
      return;
    }
    setErrors({});
    setSaving(true);
    try {
      const res = await authAPI.changePassword({
        current_password: form.current, new_password: form.next,
      });
      localStorage.setItem('access_token', res.data.tokens.access);
      localStorage.setItem('refresh_token', res.data.tokens.refresh);
      setDone(true);
    } catch (err) {
      const data = err.response?.data || {};
      setErrors({
        current: data.current_password?.[0],
        next: (data.new_password || []).join(' '),
        form: !data.current_password && !data.new_password
          ? 'Could not change your password. Please try again.' : undefined,
      });
    } finally {
      setSaving(false);
    }
  };

  const input = (key, label, error) => (
    <label style={styles.label}>
      {label}
      <input type="password" autoComplete={key === 'current' ? 'current-password' : 'new-password'}
        style={{ ...styles.input, ...(error ? styles.inputError : {}) }}
        value={form[key]} onChange={e => setForm({ ...form, [key]: e.target.value })} required />
      {error && <span style={styles.error}>{error}</span>}
    </label>
  );

  return (
    <>
      <div style={rowStyle} onClick={() => setOpen(true)}>
        <FiKey style={iconStyle} /> Change Password
      </div>

      {open && (
        <div style={styles.overlay} onClick={close}>
          <div style={styles.modal} onClick={e => e.stopPropagation()} role="dialog"
               aria-label="Change password">
            <div style={styles.header}>
              <h2 style={styles.title}>Change Password</h2>
              <FiX style={styles.closeIcon} onClick={close} aria-label="Close" />
            </div>
            {done ? (
              <>
                <p style={styles.success}>
                  Your password has been changed. You have been signed out on your other devices.
                </p>
                <button style={styles.button} onClick={close}>Done</button>
              </>
            ) : (
              <form onSubmit={submit}>
                {input('current', 'Current password', errors.current)}
                {input('next', 'New password', errors.next)}
                {input('confirm', 'Confirm new password', errors.confirm)}
                <p style={styles.hint}>
                  Use at least 8 characters. Avoid common words, only numbers, or your name.
                </p>
                {errors.form && <p style={styles.error}>{errors.form}</p>}
                <button type="submit" style={styles.button} disabled={saving}>
                  {saving ? 'Saving...' : 'Change Password'}
                </button>
              </form>
            )}
          </div>
        </div>
      )}
    </>
  );
}

const styles = {
  overlay: { position: 'fixed', inset: 0, background: 'rgba(15, 32, 53, 0.55)',
             display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 },
  modal: { background: '#fff', borderRadius: 12, padding: 24, width: 380, maxWidth: '90vw',
           boxShadow: '0 10px 30px rgba(0,0,0,0.2)', fontFamily: 'Inter, sans-serif' },
  header: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 },
  title: { fontSize: 18, fontWeight: 700, color: '#1A3A5C', margin: 0 },
  closeIcon: { width: 18, height: 18, color: '#6B7280', cursor: 'pointer' },
  label: { display: 'flex', flexDirection: 'column', gap: 6, fontSize: 13, fontWeight: 600,
           color: '#374151', marginTop: 14 },
  input: { borderWidth: 1, borderStyle: 'solid', borderColor: '#E5E7EB', borderRadius: 8,
           padding: '10px 12px', fontSize: 14, outline: 'none', fontWeight: 400 },
  inputError: { borderColor: '#EF4444' },
  error: { color: '#C0392B', fontSize: 12, fontWeight: 400 },
  hint: { fontSize: 12, color: '#6B7280', margin: '14px 0 0' },
  success: { fontSize: 14, color: '#1A6E3C', lineHeight: 1.5 },
  button: { width: '100%', marginTop: 18, background: '#1A6E3C', color: '#fff', border: 'none',
            borderRadius: 8, padding: '12px 0', fontSize: 14, fontWeight: 700, cursor: 'pointer' },
};
