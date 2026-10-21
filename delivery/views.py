from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.urls import reverse

from .models import Customer, Restaurant, Item, Cart

import razorpay
from django.conf import settings


def cart_context_for_customer(customer):
    cart = Cart.objects.filter(customer=customer).first()
    if not cart:
        return {
            'cart_items': [],
            'cart_count': 0,
            'total_price': 0,
            'cart_has_items': False,
        }
    items = list(cart.items.all())
    return {
        'cart_items': items,
        'cart_count': len(items),
        'total_price': cart.total_price(),
        'cart_has_items': len(items) > 0,
    }


def customer_page_context(customer, **extra):
    return {**cart_context_for_customer(customer), **extra}


# Create your views here.
def index(request):
    return render(request, 'delivery/index.html')

def open_signin(request):
    return render(request, 'delivery/signin.html')

def open_signup(request):
    return render(request, 'delivery/signup.html')

def signup(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        email = request.POST.get('email')
        mobile = request.POST.get('mobile')
        address = request.POST.get('address')

        try:
            Customer.objects.get(username = username)
            return HttpResponse("Duplicate username!")
        except:
            Customer.objects.create(
                username = username,
                password = password,
                email = email,
                mobile = mobile,
                address = address,
            )
    return render(request, 'delivery/signin.html')


def signin(request):
    if request.method != 'POST':
        return redirect('open_signin')
    username = request.POST.get('username')
    password = request.POST.get('password')
    try:
        Customer.objects.get(username=username, password=password)
        if username == 'admin':
            return render(request, 'delivery/admin_home.html')
        return redirect('customer_restaurants', username=username)
    except Customer.DoesNotExist:
        return render(request, 'delivery/fail.html')


def customer_restaurants(request, username):
    customer = Customer.objects.filter(username=username).first()
    if not customer:
        return redirect('open_signin')
    restaurant_list = Restaurant.objects.all()
    return render(
        request,
        'delivery/customer_home.html',
        customer_page_context(
            customer,
            restaurantList=restaurant_list,
            username=username,
        ),
    )
    
def open_add_restaurant(request):
    return render(request, 'delivery/add_restaurant.html')

def add_restaurant(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        picture = request.POST.get('picture')
        cuisine = request.POST.get('cuisine')
        rating = request.POST.get('rating')
        
        try:
            Restaurant.objects.get(name = name)
            return HttpResponse("Duplicate restaurant!")
        except:
            Restaurant.objects.create(
                name = name,
                picture = picture,
                cuisine = cuisine,
                rating = rating,
            )
    return render(request, 'delivery/admin_home.html')

def open_show_restaurant(request):
    restaurantList = Restaurant.objects.all()
    return render(request, 'delivery/show_restaurants.html',{"restaurantList" : restaurantList})

def open_update_restaurant(request, restaurant_id):
    restaurant = Restaurant.objects.get(id = restaurant_id)
    return render(request, 'delivery/update_restaurant.html', {"restaurant" : restaurant})

def update_restaurant(request, restaurant_id):
    restaurant = Restaurant.objects.get(id = restaurant_id)
    if request.method == 'POST':
        name = request.POST.get('name')
        picture = request.POST.get('picture')
        cuisine = request.POST.get('cuisine')
        rating = request.POST.get('rating')
        
        restaurant.name = name
        restaurant.picture = picture
        restaurant.cuisine = cuisine
        restaurant.rating = rating

        restaurant.save()

    restaurantList = Restaurant.objects.all()
    return render(request, 'delivery/show_restaurants.html',{"restaurantList" : restaurantList})


def delete_restaurant(request, restaurant_id):
    restaurant = Restaurant.objects.get(id = restaurant_id)
    restaurant.delete()

    restaurantList = Restaurant.objects.all()
    return render(request, 'delivery/show_restaurants.html',{"restaurantList" : restaurantList})


def open_update_menu(request, restaurant_id):
    restaurant = Restaurant.objects.get(id = restaurant_id)
    itemList = restaurant.items.all()
    #itemList = Item.objects.all()
    return render(request, 'delivery/update_menu.html',{"itemList" : itemList, "restaurant" : restaurant})
    
def update_menu(request, restaurant_id):
    restaurant = Restaurant.objects.get(id = restaurant_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        price = request.POST.get('price')
        vegeterian = request.POST.get('vegeterian') == 'on'
        picture = request.POST.get('picture')
        
        try:
            Item.objects.get(name = name)
            return HttpResponse("Duplicate item!")
        except:
            Item.objects.create(
                restaurant = restaurant,
                name = name,
                description = description,
                price = price,
                vegeterian = vegeterian,
                picture = picture,
            )
    return render(request, 'delivery/admin_home.html')

def view_menu(request, restaurant_id, username):
    customer = get_object_or_404(Customer, username=username)
    restaurant = Restaurant.objects.get(id=restaurant_id)
    itemList = restaurant.items.all()
    return render(
        request,
        'delivery/customer_menu.html',
        customer_page_context(
            customer,
            itemList=itemList,
            restaurant=restaurant,
            username=username,
        ),
    )

def add_to_cart(request, item_id, username):
    item = get_object_or_404(Item, id=item_id)
    customer = get_object_or_404(Customer, username=username)

    cart, _created = Cart.objects.get_or_create(customer=customer)
    cart.items.add(item)

    return redirect(f"{reverse('show_cart', kwargs={'username': username})}?added=1")


def remove_from_cart(request, item_id, username):
    item = get_object_or_404(Item, id=item_id)
    customer = get_object_or_404(Customer, username=username)
    cart = Cart.objects.filter(customer=customer).first()
    if cart:
        cart.items.remove(item)

    if request.GET.get("next") == "cart":
        return redirect("show_cart", username=username)
    return redirect("view_menu", restaurant_id=item.restaurant_id, username=username)

def show_cart(request, username):
    customer = get_object_or_404(Customer, username=username)
    ctx = customer_page_context(customer, username=username)
    ctx['itemList'] = ctx['cart_items']
    ctx['just_added'] = request.GET.get('added') == '1'
    return render(request, 'delivery/cart.html', ctx)

# Checkout View
def checkout(request, username):
    # Fetch customer and their cart
    customer = get_object_or_404(Customer, username=username)
    cart = Cart.objects.filter(customer=customer).first()
    cart_items = cart.items.all() if cart else []
    total_price = cart.total_price() if cart else 0

    cart_ctx = cart_context_for_customer(customer)
    if total_price == 0:
        return render(
            request,
            'delivery/checkout.html',
            {
                'error': 'Your cart is empty!',
                'username': username,
                **cart_ctx,
            },
        )

    # Initialize Razorpay client
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    # Create Razorpay order
    order_data = {
        'amount': int(total_price * 100),  # Amount in paisa
        'currency': 'INR',
        'payment_capture': '1',  # Automatically capture payment
    }
    order = client.order.create(data=order_data)

    # Pass the order details to the frontend
    return render(
        request,
        'delivery/checkout.html',
        {
            'username': username,
            'cart_items': cart_items,
            'total_price': total_price,
            'razorpay_key_id': settings.RAZORPAY_KEY_ID,
            'order_id': order['id'],
            'amount': total_price,
            'amount_paisa': int(total_price * 100),
            **cart_ctx,
        },
    )


# Orders Page
def orders(request, username):
    customer = get_object_or_404(Customer, username=username)
    cart = Cart.objects.filter(customer=customer).first()

    # Fetch cart items and total price before clearing the cart
    cart_items = cart.items.all() if cart else []
    total_price = cart.total_price() if cart else 0

    # Clear the cart after fetching its details
    if cart:
        cart.items.clear()

    return render(request, 'delivery/orders.html', {
        'username': username,
        'customer': customer,
        'cart_items': cart_items,
        'total_price': total_price,
    })
