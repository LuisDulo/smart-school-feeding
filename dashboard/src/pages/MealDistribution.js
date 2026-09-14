import React, { useState, useEffect } from 'react';
import { FiUsers, FiBarChart2 } from 'react-icons/fi';
import { MdOutlineRestaurant } from 'react-icons/md';
import Topbar from '../components/Topbar';
import { mealsAPI } from '../services/api';

export default function MealDistribution() {
  const [log, setLog] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedDate, setSelectedDate] = useState(
    new Date().toISOString().split('T')[0]);

  const loadLog = async (dateStr) => {
    setLoading(true);
    try {
      const res = await mealsAPI.log(dateStr);
      setLog(res.data);
    } catch (e) {
      console.error('Log error:', e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadLog(selectedDate); }, [selectedDate]);

  return (
    <div style={styles.page}>
      <Topbar
        title="Meal Distribution"
        subtitle="Daily meal collection log"
      />
      <div style={styles.content}>
        <div style={styles.toolbar}>
          <input
            type="date"
            style={styles.datePicker}
            value={selectedDate}
            onChange={e => setSelectedDate(e.target.value)}
          />
          {log && (
            <div style={styles.summary}>
              <span style={styles.summaryItem}>
                <MdOutlineRestaurant style={styles.summaryIcon} />
                <strong>{log.total_meals_served}</strong> meals served
              </span>
              <span style={styles.summaryItem}>
                <FiUsers style={styles.summaryIcon} />
                <strong>{log.enrolment}</strong> enrolled
              </span>
              <span style={styles.summaryItem}>
                <FiBarChart2 style={styles.summaryIcon} />
                <strong>
                  {(log.attendance_rate * 100).toFixed(1)}%
                </strong> attendance
              </span>
            </div>
          )}
        </div>

        <div style={styles.tableWrap}>
          <table style={styles.table}>
            <thead>
              <tr style={styles.thead}>
                {['#', 'Student Name', 'Items Collected', 'Amount (KES)',
                  'Time Served', 'Served By', 'Balance After (KES)'].map(h => (
                  <th key={h} style={styles.th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={7} style={styles.empty}>Loading...</td></tr>
              ) : !log || log.events.length === 0 ? (
                <tr>
                  <td colSpan={7} style={styles.empty}>
                    No meals recorded for {selectedDate}
                  </td>
                </tr>
              ) : log.events.map((event, i) => (
                <tr key={event.id}
                  style={i % 2 === 0 ? styles.trEven : styles.trOdd}>
                  <td style={styles.td}>{i + 1}</td>
                  <td style={{ ...styles.td, fontWeight: 600 }}>
                    {event.student_name}
                  </td>
                  <td style={styles.td}>
                    {event.items && event.items.length > 0
                      ? event.items.map(it => it.name).join(', ')
                      : '—'}
                  </td>
                  <td style={{ ...styles.td, fontWeight: 600 }}>
                    {event.amount_ksh?.toLocaleString('en-KE',
                      { minimumFractionDigits: 2 })}
                  </td>
                  <td style={styles.td}>
                    {new Date(event.created_at).toLocaleTimeString(
                      'en-KE', { hour: '2-digit', minute: '2-digit' })}
                  </td>
                  <td style={styles.td}>
                    {event.served_by_name}
                    <div style={styles.subtle}>{event.served_by_email}</div>
                  </td>
                  <td style={{
                    ...styles.td,
                    color: event.balance_after_ksh < 100
                      ? '#C0392B' : '#1A6E3C',
                    fontWeight: 700
                  }}>
                    {event.balance_after_ksh?.toLocaleString('en-KE',
                      { minimumFractionDigits: 2 })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

const styles = {
  page: { flex: 1, display: 'flex', flexDirection: 'column',
          background: '#F7F9FC', overflow: 'auto' },
  content: { padding: 32 },
  toolbar: { display: 'flex', gap: 20, marginBottom: 20,
             alignItems: 'center', flexWrap: 'wrap' },
  datePicker: { border: '1px solid #E5E7EB', borderRadius: 8,
                padding: '10px 14px', fontSize: 14, outline: 'none' },
  summary: { display: 'flex', gap: 20 },
  summaryItem: { fontSize: 13, color: '#374151',
                 background: '#fff', padding: '8px 16px',
                 borderRadius: 8, border: '1px solid #E5E7EB',
                 display: 'flex', alignItems: 'center', gap: 8 },
  summaryIcon: { width: 15, height: 15, color: '#6B7280', flexShrink: 0 },
  tableWrap: { background: '#fff', borderRadius: 12, overflow: 'hidden',
               boxShadow: '0 2px 8px rgba(0,0,0,0.04)' },
  table: { width: '100%', borderCollapse: 'collapse' },
  thead: { background: '#1A3A5C' },
  th: { padding: '14px 20px', textAlign: 'left',
        fontSize: 12, fontWeight: 700, color: '#fff' },
  trEven: { background: '#fff' },
  trOdd: { background: '#F9FAFB' },
  td: { padding: '14px 20px', fontSize: 13, color: '#374151',
        borderBottom: '1px solid #F3F4F6' },
  empty: { padding: 40, textAlign: 'center',
           color: '#9CA3AF', fontSize: 14 },
  subtle: { fontSize: 11, color: '#9CA3AF', marginTop: 2 },
};
