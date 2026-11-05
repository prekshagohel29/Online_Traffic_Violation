import { render, screen } from '@testing-library/react';
import App from './App';

test('portal has no public hardware submission or demo login shortcuts', async () => {
  render(<App />);
  expect(await screen.findByRole('heading',{name:'Welcome to e-Memo System'})).toBeInTheDocument();
  expect(screen.getByRole('button',{name:/Vehicle Owner/})).toBeInTheDocument();
  expect(screen.queryByText('Hardware API Test')).not.toBeInTheDocument();
});
