### Project Name: RetailPrime

## Project Description
RetailPrime is a single-vendor ecommerce platform designed to facilitate online retail operations for a professional store. The system allows a vendor (store owner/admin) to manage products, categories, inventory, orders, coupons, and reviews, while providing customers with a seamless shopping experience through browsing, cart management, checkout, and order tracking.

The platform is built as a RESTful API, intended to serve a frontend web or mobile application. It is structured for scalability, enabling the vendor to expand beyond a single product niche over time.

## RetailPrime emphasizes:
    Ease of use for both the admin/vendor and customers
    Security in authentication and payment processes
    Maintainability through a clean separation of models and responsibilities
    Performance for handling product browsing, cart updates, and order processing efficiently
    
## Key Features:
# For Customers:
User registration and authentication
Profile and address management
Product browsing and search by category or keyword
Add products to a single active cart
Apply coupons/discounts
Checkout and make payments
View order history and order details
Submit reviews for purchased products
Maintain a wishlist for future purchases


# For Vendor/Admin:
Manage categories and products (add, update, activate/deactivate)
Manage inventory and stock levels
View and process orders (update order status: pending, shipped, delivered, canceled)
Create and manage coupons/promotions
Moderate product reviews
View carts for support or analytics purposes (read-only recommended)
Access via Django admin panel using is_staff and is_superuser privileges


## Models and Responsibilities
# Model           Purpose                                     Responsible Party
User            Stores customer and admin accounts          Customers create themselves; Admin manages users in admin panel
Address         Stores shipping/billing addresses           Customers manage; Admin views for orders
Category        Organizes products for browsing             Admin manages
Product         Represents items for sale                   Admin manages
ProductImage    Product visuals                             Admin manages
Cart            Single active shopping cart per customer    System creates; Customer manages items
CartItem        Individual items in a cart                  Customer manages; Admin views only
Order           Completed purchases                         Customer places; Admin manages fulfillment
OrderItem       Products in an order                        System generates; Admin/Customer views
Inventory       Tracks stock                                Admin manages; System updates after orders
Coupon          Discount codes                              Admin manages; Customer applies on checkout
Payment         Tracks payment status                       Customer initiates; System processes; Admin monitors
PaymentMethod   stores different payment method options     Admin manages; customers view and choose a method
Review          Customer product ratings                    Customer creates; Admin moderates
Wishlist        Customer saved items                        Customer manages


## Entity Relationship Diagram
<img width="1238" height="1338" alt="RetailPrime ERD diagram drawio" src="https://github.com/user-attachments/assets/b65bbe16-6791-48ed-9329-b031b9abb172" />


## Functional Requirements
# Authentication & Authorization:
Customer registration and login (JWT/Token-based auth)
Admin login via Django admin (no public admin signup)


# Product Management:
Add, update, delete products
Assign products to categories
Upload product images
Track inventory stock


# Cart & Checkout:
Single active cart per user
Add, update, remove items in cart
Apply coupons during checkout
Convert cart to order after successful payment


# Order Management:
View order history (customer)
Update order status (admin)
View order items, shipping address, and payment info


# Payment:
Integrate with payment gateway
Track payment status: pending, success, failed


# Customer Engagement:
Submit reviews on purchased products
Maintain a wishlist
Search and filter products by category, price, or keyword


## Non-Functional Requirements:
# Performance:
API should handle multiple concurrent users efficiently
Paginate product lists and order lists to avoid large payloads


# Security:
Passwords hashed and stored securely
JWT or token-based authentication for API endpoints
Admin operations restricted to is_staff/is_superuser users
Sensitive data (payment info) encrypted or not stored directly


# Scalability:
Designed to support future addition of new product categories or multi-category expansion
Database design supports many products, orders, and users


# Maintainability:
Modular model design with clear separation of responsibilities
RESTful endpoints follow consistent conventions


# Reliability:
Ensure cart persistence for active users
Handle payment failures gracefully
Order integrity maintained (inventory adjusted only on successful orders)


# Usability:
Customers have a seamless shopping experience
Admin can efficiently manage products and orders from Django admin


## RetailPrime API Endpoint Structure
# Authentication & User Management:
Endpoint                Method          Description                         Access
/auth/register/         POST            Register a new customer             Customer
/auth/login/            POST            Obtain token / login                Customer
/auth/logout/           POST            Logout / revoke token               Customer
/auth/profile/          GET, PUT        View/update user profile            Customer
/auth/change-password   /POST           Change password                     Customer

# Note: Admin logs in via Django admin; no API signup.

# Address Management
Endpoint            Method                  Description                                             Access
/addresses/         GET                     List all addresses                                      Customer
/addresses/         POST                    Add a new address                                       Customer
/addresses/{id}/    GET, PUT, DELETE        Retrieve, update, or delete a specific address          Customer


# Category Management
Endpoint                Method          Description                 Access
/categories/            GET             List all categories         Public / Customer
/categories/{id}/       GET             View category details       Public / Customer
/categories/            POST            Create a new category       Admin
/categories/{id}/       PUT, DELETE     Update or delete category   Admin


# Product Management
Endpoint                            Method          Description                                     Access
/products/                          GET             List all products, with filtering & search      Public / Customer
/products/{id}/                     GET             Retrieve product details                        Public / Customer
/products/                          POST            Create a new product                            Admin
/products/{id}/                     PUT, DELETE     Update or delete product                        Admin
/products/{id}/images/              POST            Add product images                              Admin
/products/{id}/images/{image_id}/   DELETE          Remove product image                            Admin


# Inventory
Endpoint                    Method      Description                 Access
/inventory/                 GET         List all inventory items    Admin
/inventory/{product_id}/    GET         View stock for a product    Admin
/inventory/{product_id}/    PUT         Update stock quantity       Admin


# Cart & Cart Items
Endpoint                Method      Description                             Access
/cart/                  GET         Get current active cart                 Customer
/cart/                  POST        Create cart (system can auto-create)    Customer
/cart/items/            POST        Add item to cart                        Customer
/cart/items/{id}/       PUT         Update quantity of an item              Customer
/cart/items/{id}/       DELETE      Remove item from cart                   Customer
/cart/checkout/         POST        Convert cart into order                 Customer

# Note: Admin can view carts via /admin (Django admin). No API modification needed.


# Order & Order Items
Endpoint                Method      Description                     Access
/orders/                GET         List user’s orders              Customer
/orders/{id}/           GET         Retrieve order details          Customer
/orders/                POST        Place order from cart           Customer
/admin/orders/          GET         List all orders                 Admin
/admin/orders/{id}/     GET, PUT    View and update order status    Admin
/orders/{id}/items/     GET         List order items                Customer/Admin


# Payment
Endpoint            Method      Description                         Access
/payments/          POST        Initiate payment for an order       Customer
/payments/{id}/     GET         View payment status                 Customer/Admin
/admin/payments/    GET         Admin view of all payments          Admin


# PaymentMethod
Endpoint	                Method	        Purpose	                    Access
/payment-methods/	        GET	            List all payment methods	Customer/Admin
/payment-methods/{id}/	    GET	            Get one payment method	    Customer/Admin
/payment-methods/	        POST	        Create payment method	    Admin only
/payment-methods/{id}/	    PUT/PATCH	    Update payment method	    Admin only
/payment-methods/{id}/	    DELETE	        Delete payment method	    Admin only

# Coupon / Discount Codes
Endpoint                   Method             Description                   Access
/coupons/                  GET                List active coupons           Customer
/coupons/apply/            POST               Apply coupon at checkout      Customer
/admin/coupons/            POST               Create new coupon             Admin
/admin/coupons/{id}/       PUT, DELETE        Update or remove coupon       Admin


# Reviews
Endpoint                    Method          Description                             Access
/products/{id}/reviews/     GET             List reviews for a product              Public / Customer
/products/{id}/reviews/     POST            Add a review for purchased product      Customer
/reviews/{id}/              PUT, DELETE     Update or delete review (moderation)    Admin


# Wishlist
Endpoint                Method          Description                         Access
/wishlist/              GET             List user wishlist                  Customer
/wishlist/              POST            Add product to wishlist             Customer
/wishlist/{id}/         DELETE          Remove product from wishlist        Customer


