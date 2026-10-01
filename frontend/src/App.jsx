import React, { useState, useEffect } from "react";

function App() {
  const [activeTab, setActiveTab] = useState("customer");
  const [products, setProducts] = useState([]);
  const [cart, setCart] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  // Search & Filter State
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("All");

  // Customer Form State
  const [customer, setCustomer] = useState({ name: "", phone: "", address: "", order_type: "Dine-in", table_number: "" });
  const [showQrModal, setShowQrModal] = useState(false);

  // Admin Security & States
  const [isAdminAuthenticated, setIsAdminAuthenticated] = useState(false);
  const [pinInput, setPinInput] = useState("");
  const [orders, setOrders] = useState([]);
  const [stats, setStats] = useState({ total_orders: 0, pending_orders: 0, completed_orders: 0, total_revenue: 0 });
  const [statusFilter, setStatusFilter] = useState("All");
  const [newProduct, setNewProduct] = useState({ name: "", price: "", category: "Tea & Coffee" });

  const ADMIN_PIN = "1234";

  const fetchProducts = async () => {
    const res = await fetch("http://localhost:8000/products");
    setProducts(await res.json());
  };

  const fetchAdminData = async () => {
    const [oRes, sRes] = await Promise.all([
      fetch("http://localhost:8000/orders"),
      fetch("http://localhost:8000/stats")
    ]);
    setOrders(await oRes.json());
    setStats(await sRes.json());
  };

  useEffect(() => {
    fetchProducts();
    if (activeTab === "admin" && isAdminAuthenticated) fetchAdminData();
  }, [activeTab, isAdminAuthenticated]);

  // Cart logic
  const addToCart = (product) => {
    setCart((prev) => {
      const exist = prev.find((i) => i.id === product.id);
      return exist
        ? prev.map((i) => (i.id === product.id ? { ...i, quantity: i.quantity + 1 } : i))
        : [...prev, { ...product, quantity: 1 }];
    });
  };

  const updateQuantity = (id, change) => {
    setCart((prev) =>
      prev.map((item) => item.id === id ? { ...item, quantity: item.quantity + change } : item).filter((i) => i.quantity > 0)
    );
  };

  const totalAmount = cart.reduce((sum, item) => sum + item.price * item.quantity, 0);

  const handlePlaceOrder = async (e) => {
    e.preventDefault();
    if (cart.length === 0) return alert("Cart खाली छ!");

    setLoading(true);
    setMessage("");

    const payload = {
      customer_name: customer.name,
      customer_phone: customer.phone,
      customer_address: customer.order_type === "Delivery" ? customer.address : "",
      order_type: customer.order_type,
      table_number: customer.order_type === "Dine-in" ? customer.table_number : "",
      items: cart.map((item) => ({ product_id: item.id, quantity: item.quantity })),
    };

    try {
      const res = await fetch("http://localhost:8000/orders", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        const data = await res.json();
        setMessage(`✅ Order Save भयो! (Order ID: ${data.order_id})`);
        setCart([]);
        setCustomer({ name: "", phone: "", address: "", order_type: "Dine-in", table_number: "" });
        setShowQrModal(false);
      }
    } catch (err) {
      setMessage("❌ Order Fail भयो।");
    } finally {
      setLoading(false);
    }
  };

  const handleAdminLogin = (e) => {
    e.preventDefault();
    if (pinInput === ADMIN_PIN) setIsAdminAuthenticated(true);
    else alert("गलत PIN कोड!");
  };

  const handleAddProduct = async (e) => {
    e.preventDefault();
    if (!newProduct.name || !newProduct.price) return;
    await fetch("http://localhost:8000/products", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: newProduct.name, price: parseFloat(newProduct.price), category: newProduct.category }),
    });
    setNewProduct({ name: "", price: "", category: "Tea & Coffee" });
    fetchProducts();
  };

  const handleDeleteProduct = async (id) => {
    if (!window.confirm("हटाउन निश्चित हुनुहुन्छ?")) return;
    await fetch(`http://localhost:8000/products/${id}`, { method: "DELETE" });
    fetchProducts();
  };

  const handleStatusChange = async (orderId, newStatus) => {
    await fetch(`http://localhost:8000/orders/${orderId}/status`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: newStatus }),
    });
    fetchAdminData();
  };

  // Filter products by Search & Category
  const categories = ["All", ...new Set(products.map((p) => p.category || "Tea & Coffee"))];
  const filteredProducts = products.filter((p) => {
    const matchesSearch = p.name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = selectedCategory === "All" || p.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  const filteredOrders = statusFilter === "All" ? orders : orders.filter((o) => o.status === statusFilter);

  return (
    <div style={{ maxWidth: "1000px", margin: "20px auto", padding: "20px", fontFamily: "Arial, sans-serif" }}>
      {/* Navigation */}
      <div style={{ display: "flex", gap: "10px", marginBottom: "20px" }}>
        <button onClick={() => setActiveTab("customer")} style={{ padding: "10px 20px", backgroundColor: activeTab === "customer" ? "#28a745" : "#ddd", color: "#fff", border: "none", borderRadius: "5px", cursor: "pointer", fontWeight: "bold" }}>
          ☕ Chiya Menu & Cart
        </button>
        <button onClick={() => setActiveTab("admin")} style={{ padding: "10px 20px", backgroundColor: activeTab === "admin" ? "#007bff" : "#ddd", color: "#fff", border: "none", borderRadius: "5px", cursor: "pointer", fontWeight: "bold" }}>
          🔒 Admin Dashboard
        </button>
      </div>

      {/* CUSTOMER VIEW */}
      {activeTab === "customer" && (
        <div>
          <h2>☕ Menu Items</h2>
          
          {/* Search & Filter Bar */}
          <div style={{ display: "flex", gap: "10px", flexWrap: "wrap", marginBottom: "20px" }}>
            <input
              type="text"
              placeholder="🔎 Search Chiya / Food..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{ padding: "8px", width: "250px", borderRadius: "4px", border: "1px solid #ccc" }}
            />
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                style={{
                  padding: "8px 12px",
                  backgroundColor: selectedCategory === cat ? "#ff9800" : "#f0f0f0",
                  color: selectedCategory === cat ? "#fff" : "#000",
                  border: "none",
                  borderRadius: "4px",
                  cursor: "pointer"
                }}
              >
                {cat}
              </button>
            ))}
          </div>

          {/* Product Items */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: "15px", marginBottom: "30px" }}>
            {filteredProducts.map((item) => (
              <div key={item.id} style={{ border: "1px solid #ccc", padding: "15px", borderRadius: "8px", textAlign: "center" }}>
                <span style={{ fontSize: "11px", backgroundColor: "#eee", padding: "2px 6px", borderRadius: "4px" }}>{item.category || "Tea & Coffee"}</span>
                <h3 style={{ margin: "5px 0" }}>{item.name}</h3>
                <p style={{ fontWeight: "bold", color: "#555" }}>रू {item.price}</p>
                <button onClick={() => addToCart(item)} style={{ padding: "8px 12px", backgroundColor: "#ff9800", color: "#fff", border: "none", borderRadius: "4px", cursor: "pointer" }}>
                  🛒 Add to Cart
                </button>
              </div>
            ))}
          </div>

          {/* Cart Section */}
          <div style={{ borderTop: "2px solid #ddd", paddingTop: "20px" }}>
            <h2>🛒 Your Cart</h2>
            {cart.length === 0 ? (
              <p>Cart खाली छ।</p>
            ) : (
              <div>
                {cart.map((item) => (
                  <div key={item.id} style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "10px", maxWidth: "450px" }}>
                    <span style={{ flex: 1 }}>{item.name} (रू {item.price})</span>
                    <button onClick={() => updateQuantity(item.id, -1)} style={{ padding: "2px 8px" }}>-</button>
                    <strong>{item.quantity}</strong>
                    <button onClick={() => updateQuantity(item.id, 1)} style={{ padding: "2px 8px" }}>+</button>
                    <span>= रू {item.price * item.quantity}</span>
                  </div>
                ))}
                <h3>Total: रू {totalAmount}</h3>

                {/* Checkout Form */}
                <form onSubmit={(e) => { e.preventDefault(); setShowQrModal(true); }} style={{ display: "flex", flexDirection: "column", gap: "10px", maxWidth: "400px", marginTop: "15px" }}>
                  <h3>👤 Customer Details</h3>
                  
                  <div style={{ display: "flex", gap: "15px" }}>
                    <label>
                      <input type="radio" name="orderType" value="Dine-in" checked={customer.order_type === "Dine-in"} onChange={() => setCustomer({ ...customer, order_type: "Dine-in" })} /> Dine-in (टेबल)
                    </label>
                    <label>
                      <input type="radio" name="orderType" value="Delivery" checked={customer.order_type === "Delivery"} onChange={() => setCustomer({ ...customer, order_type: "Delivery" })} /> Home Delivery
                    </label>
                  </div>

                  <input type="text" placeholder="Full Name" value={customer.name} onChange={(e) => setCustomer({ ...customer, name: e.target.value })} required style={{ padding: "8px" }} />
                  <input type="text" placeholder="Phone Number" value={customer.phone} onChange={(e) => setCustomer({ ...customer, phone: e.target.value })} required style={{ padding: "8px" }} />
                  
                  {customer.order_type === "Dine-in" ? (
                    <input type="text" placeholder="Table Number (eg. T-4)" value={customer.table_number} onChange={(e) => setCustomer({ ...customer, table_number: e.target.value })} required style={{ padding: "8px" }} />
                  ) : (
                    <textarea placeholder="Delivery Address" value={customer.address} onChange={(e) => setCustomer({ ...customer, address: e.target.value })} required rows="2" style={{ padding: "8px" }} />
                  )}

                  <button type="submit" style={{ padding: "10px", backgroundColor: "#28a745", color: "#fff", border: "none", borderRadius: "4px", cursor: "pointer", fontWeight: "bold" }}>
                    💳 Proceed to Pay & Order (रू {totalAmount})
                  </button>
                </form>
              </div>
            )}
            {message && <p style={{ marginTop: "10px", fontWeight: "bold" }}>{message}</p>}
          </div>

          {/* Fonepay / eSewa Dynamic QR Modal */}
          {showQrModal && (
            <div style={{ position: "fixed", top: 0, left: 0, width: "100%", height: "100%", backgroundColor: "rgba(0,0,0,0.5)", display: "flex", justifyContent: "center", alignItems: "center" }}>
              <div style={{ backgroundColor: "#fff", padding: "20px", borderRadius: "8px", textAlign: "center", maxWidth: "350px" }}>
                <h3>📱 Scan to Pay with eSewa / Fonepay</h3>
                <p>Total Amount: <strong>रू {totalAmount}</strong></p>
                <img src={`https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=ChiyaPasal_NPR_${totalAmount}`} alt="QR Code" style={{ margin: "15px 0" }} />
                <p style={{ fontSize: "12px", color: "#666" }}>स्क्यान गरी Payment गरेपछि तलको बटन थिच्नुहोस्</p>
                <div style={{ display: "flex", gap: "10px", justifyContent: "center" }}>
                  <button onClick={handlePlaceOrder} disabled={loading} style={{ padding: "10px 15px", backgroundColor: "#28a745", color: "#fff", border: "none", borderRadius: "4px", cursor: "pointer" }}>
                    {loading ? "Processing..." : "Confirm & Complete Order"}
                  </button>
                  <button onClick={() => setShowQrModal(false)} style={{ padding: "10px 15px", backgroundColor: "#dc3545", color: "#fff", border: "none", borderRadius: "4px", cursor: "pointer" }}>
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ADMIN PANEL VIEW */}
      {activeTab === "admin" && (
        <div>
          {!isAdminAuthenticated ? (
            <div style={{ maxWidth: "350px", margin: "50px auto", padding: "20px", border: "1px solid #ccc", borderRadius: "8px", textAlign: "center" }}>
              <h2>🔒 Admin PIN Authorization</h2>
              <form onSubmit={handleAdminLogin}>
                <input type="password" placeholder="PIN (Default: 1234)" value={pinInput} onChange={(e) => setPinInput(e.target.value)} style={{ padding: "10px", width: "80%", marginBottom: "10px", textAlign: "center" }} required />
                <button type="submit" style={{ padding: "10px 20px", backgroundColor: "#007bff", color: "#fff", border: "none", borderRadius: "4px", cursor: "pointer" }}>Unlock Dashboard</button>
              </form>
            </div>
          ) : (
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <h2>📊 Admin Dashboard</h2>
                <button onClick={() => setIsAdminAuthenticated(false)} style={{ padding: "5px 10px", backgroundColor: "#dc3545", color: "#fff", border: "none", borderRadius: "4px" }}>Lock Panel</button>
              </div>

              {/* Add Product Form */}
              <div style={{ backgroundColor: "#f9f9f9", padding: "15px", borderRadius: "8px", marginBottom: "20px" }}>
                <h3>➕ Add New Item to Menu</h3>
                <form onSubmit={handleAddProduct} style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
                  <input type="text" placeholder="Item Name" value={newProduct.name} onChange={(e) => setNewProduct({ ...newProduct, name: e.target.value })} required style={{ padding: "8px" }} />
                  <input type="number" placeholder="Price" value={newProduct.price} onChange={(e) => setNewProduct({ ...newProduct, price: e.target.value })} required style={{ padding: "8px", width: "100px" }} />
                  <select value={newProduct.category} onChange={(e) => setNewProduct({ ...newProduct, category: e.target.value })} style={{ padding: "8px" }}>
                    <option value="Tea & Coffee">Tea & Coffee</option>
                    <option value="Snacks">Snacks</option>
                    <option value="Cold Drinks">Cold Drinks</option>
                    <option value="Bakery">Bakery</option>
                  </select>
                  <button type="submit" style={{ padding: "8px 15px", backgroundColor: "#28a745", color: "#fff", border: "none", borderRadius: "4px" }}>Add Product</button>
                </form>
              </div>

              {/* Orders Table */}
              <h3>📋 Customer Orders</h3>
              <table border="1" cellPadding="8" style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ backgroundColor: "#f2f2f2" }}>
                    <th>ID</th>
                    <th>Type / Location</th>
                    <th>Customer</th>
                    <th>Items</th>
                    <th>Total</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredOrders.map((o) => (
                    <tr key={o.id}>
                      <td>#{o.id}</td>
                      <td>
                        <strong>{o.order_type}</strong><br />
                        {o.order_type === "Dine-in" ? `🪑 Table: ${o.table_number}` : `📍 ${o.customer_address}`}
                      </td>
                      <td>{o.customer_name}<br />📞 {o.customer_phone}</td>
                      <td>{o.items.map((i) => <div key={i.id}>{i.product_name} x {i.quantity}</div>)}</td>
                      <td>रू {o.total_price}</td>
                      <td>
                        <select value={o.status} onChange={(e) => handleStatusChange(o.id, e.target.value)} style={{ padding: "4px" }}>
                          <option value="Pending">Pending</option>
                          <option value="Preparing">Preparing</option>
                          <option value="Completed">Completed</option>
                        </select>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default App;