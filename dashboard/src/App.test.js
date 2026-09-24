import { render, screen } from '@testing-library/react';
import App from './App';

test('renders the admin sign in form when logged out', () => {
  localStorage.clear();
  render(<App />);
  const heading = screen.getByText(/Administrator Sign In/i);
  expect(heading).toBeInTheDocument();
});
