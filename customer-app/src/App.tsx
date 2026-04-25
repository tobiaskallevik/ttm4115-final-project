import { useState, useEffect } from 'react';

const API_BASE = 'http://localhost:8000/api/orders';

function App() {
  const [orderId, setOrderId] = useState<number | null>(null);
  const [status, setStatus] = useState<string>('browsing');

  useEffect(() => {
    if (!orderId) return;
    const interval = setInterval(async () => {
      try {
        const response = await fetch(`${API_BASE}/${orderId}/`);
        const data = await response.json();
        setStatus(data.status);
      } catch (e) { console.error(e); }
    }, 1000);
    return () => clearInterval(interval);
  }, [orderId]);

  const placeOrder = async () => {
    const response = await fetch(`${API_BASE}/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ restaurant: 1, customer_name: "Test User", landing_lat: 63.4305, landing_lng: 10.3951 })
    });
    const data = await response.json();
    setOrderId(data.id);
    setStatus(data.status ?? 'pending');
  };

  const sendTrigger = async (action: string) => {
    if (!orderId) return;
    try {
      const response = await fetch(`${API_BASE}/${orderId}/trigger_drone/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action })
      });

      if (response.ok) {
        const data = await response.json();
        setStatus(data.order_status);
      } else {
        const errorData = await response.json();
        console.error("Transition blocked:", errorData.error);
        alert(`Action failed: ${errorData.error}`);
      }
    } catch (e) {
      console.error("Connection error:", e);
    }
  };

  return (
    <div style={{ padding: '20px', fontFamily: 'sans-serif', maxWidth: '500px' }}>
      <h1>Drone Delivery App </h1>

      {status === 'browsing' && (
        <div style={{ border: '1px solid #ccc', padding: '15px' }}>
          <h3>Margherita Pizza - 200kr</h3>
          <button onClick={placeOrder} style={{ padding: '10px', background: '#007BFF', color: 'white' }}>
            Buy Now
          </button>
        </div>
      )}

      {orderId && (
        <div style={{ marginTop: '20px', padding: '15px', background: '#f5f5f5', borderRadius: '8px' }}>
          <h2>Tracking Order #{orderId}</h2>
          <p>Current Status: <strong>{status}</strong></p>

          {status === 'pending' && <p>Waiting for restaurant to accept your order...</p>}
          {status === 'accepted' && <p>The restaurant has accepted your order.</p>}
          {status === 'ready' && <p>Your food is ready. Dispatching a drone now.</p>}
          {status === 'loaded' && <p>Food is loaded into the drone.</p>}
          {status === 'in_transit' && <p>Drone is on the way.</p>}
          {status === 'arrived' && (
            <div>
              <p>Drone is hovering nearby and waiting for presence confirmation.</p>
              <button onClick={() => sendTrigger('presence_confirmed')} style={{ padding: '10px', background: '#0b5ed7', color: 'white' }}>
                Confirm Presence
              </button>
            </div>
          )}

          {status === 'delivering' && (
            <button onClick={() => sendTrigger('delivered')} style={{ padding: '10px', background: 'green', color: 'white' }}>
              I have retrieved my food!
            </button>
          )}

          {status === 'delivered' && <p>Delivery complete. Enjoy your meal!</p>}
          {status === 'stuck' && <p>Package got stuck. Restaurant support has been notified.</p>}
          {status === 'failed' && <p>Delivery failed. Please contact support or place a new order.</p>}
        </div>
      )}
    </div>
  );
}

export default App;