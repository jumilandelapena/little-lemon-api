from django.urls import path

from . import views

urlpatterns = [
    # Categories
    path("categories/", views.CategoriesView.as_view(), name="categories"),
    path("categories/<int:pk>/", views.CategoryDetailView.as_view(), name="category-detail"),
    # Menu items
    path("menu-items/", views.MenuItemsView.as_view(), name="menu-items"),
    path("menu-items/<int:pk>/", views.MenuItemDetailView.as_view(), name="menu-item-detail"),
    # User group management
    path("groups/manager/users/", views.ManagerUsersView.as_view(), name="manager-users"),
    path(
        "groups/manager/users/<int:userId>/",
        views.ManagerUserDetailView.as_view(),
        name="manager-user-detail",
    ),
    path(
        "groups/delivery-crew/users/",
        views.DeliveryCrewUsersView.as_view(),
        name="delivery-crew-users",
    ),
    path(
        "groups/delivery-crew/users/<int:userId>/",
        views.DeliveryCrewUserDetailView.as_view(),
        name="delivery-crew-user-detail",
    ),
    # Cart
    path("cart/menu-items/", views.CartView.as_view(), name="cart"),
    # Orders
    path("orders/", views.OrdersView.as_view(), name="orders"),
    path("orders/<int:pk>/", views.OrderDetailView.as_view(), name="order-detail"),
]
