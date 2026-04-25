import { useState, useEffect } from 'react';

interface Order {
  id: number;
  customer_name: string;
  status: string;
}

const API_BASE = 'http://localhost:8000/api/orders';

function App() {
  const [orders, setOrders] = useState<Order[]>([]);

  const fetchOrders = async () => {
    try {
      const response = await fetch(`${API_BASE}/`);
      setOrders(await response.json());
    } catch (error) { console.error("Failed to fetch", error); }
  };

  useEffect(() => {
    fetchOrders();
    const interval = setInterval(fetchOrders, 1000);
    return () => clearInterval(interval);
  }, []);

  const sendTrigger = async (orderId: number, action: string) => {
    await fetch(`${API_BASE}/${orderId}/trigger_drone/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action })
    });
    fetchOrders();
  };

  const postAction = async (orderId: number, path: string) => {
    await fetch(`${API_BASE}/${orderId}/${path}/`, {
      method: 'POST'
    });
    fetchOrders();
  };

  return (
    <div style={{ padding: '20px', fontFamily: 'sans-serif', maxWidth: '600px' }}>
      <h1>Restaurant Dashboard</h1>

      {orders.map(order => (
        <div key={order.id} style={{ border: '2px solid #333', margin: '10px 0', padding: '15px', borderRadius: '8px' }}>
          <h3>Order #{order.id} - {order.customer_name}</h3>
          <p><strong>Drone State:</strong> <span style={{ color: 'blue', fontSize: '1.2em' }}>{order.status}</span></p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {order.status === 'pending' && (
              <button onClick={() => postAction(order.id, 'accept')} style={{ background: 'green', color: 'white', padding: '10px' }}>
                Accept Order
              </button>
            )}

            {order.status === 'accepted' && (
              <button onClick={() => postAction(order.id, 'mark_ready')} style={{ background: '#0a7', color: 'white', padding: '10px' }}>
                Mark Food Ready
              </button>
            )}

            {order.status === 'ready' && (
              <button onClick={() => sendTrigger(order.id, 'order')} style={{ background: '#0b5ed7', color: 'white', padding: '10px' }}>
                Dispatch Drone to Restaurant
              </button>
            )}

            {order.status === 'loaded' && (
              <button onClick={() => sendTrigger(order.id, 'pickup_complete')} style={{ background: 'purple', color: 'white', padding: '10px' }}>
                Food Loaded. Send Drone to Customer
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

export default App;