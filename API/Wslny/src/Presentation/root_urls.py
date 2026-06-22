from django.contrib import admin
from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenRefreshView

from src.Presentation.views.auth_views import (
    ChangePasswordView,
    GoogleLoginView,
    LoginView,
    ProfileView,
    RegisterView,
)
from src.Presentation.views.admin_views import (
    ChangeUserRoleView,
    RouteAnalyticsOverviewView,
    RouteAnalyticsQueryView,
    RouteFilterStatsView,
    RouteAnalyticsTopRoutesView,
    RouteUnresolvedStatsView,
    UserListView,
)
from src.Presentation.views.orchestrator import RouteOrchestratorView
from src.Presentation.views.orchestrator import RouteHistoryView
from src.Presentation.views.orchestrator import RouteSearchView
from src.Presentation.views.orchestrator import RouteSearchConfirmView
from src.Presentation.views.orchestrator import RouteMetadataView
from src.Presentation.views.health_views import HealthView
from src.Presentation.views.transit_views import (
    NearbyStopsView,
    StopDetailView,
    LinesView,
    LineDetailView,
)
from src.Presentation.views.user_views import (
    SavedLocationsView,
    SavedLocationDetailView,
    FavoriteRoutesView,
    FavoriteRouteDetailView,
    UserPreferencesView,
)
from src.Presentation.views.route_views import (
    RouteAlternativesView,
    RouteFeedbackView,
)
from src.Presentation.views.admin_management_views import (
    AdminUserDetailView,
    UserAnalyticsOverviewView,
    FeedbackAnalyticsView,
    FeedbackSummaryView,
)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/auth/register", RegisterView.as_view(), name="register"),
    path("api/v1/auth/login", LoginView.as_view(), name="login"),
    path("api/v1/auth/google-login", GoogleLoginView.as_view(), name="google-login"),
    path("api/v1/auth/profile", ProfileView.as_view(), name="profile"),
    path(
        "api/v1/auth/change-password",
        ChangePasswordView.as_view(),
        name="change-password",
    ),
    path("api/v1/auth/refresh", TokenRefreshView.as_view(), name="token-refresh"),
    path("api/v1/admin/change-role", ChangeUserRoleView.as_view(), name="change-role"),
    path("api/v1/admin/users", UserListView.as_view(), name="list-users"),
    path(
        "api/v1/admin/analytics/routes/overview",
        RouteAnalyticsOverviewView.as_view(),
        name="routes-analytics-overview",
    ),
    path(
        "api/v1/admin/analytics/routes/top-routes",
        RouteAnalyticsTopRoutesView.as_view(),
        name="routes-analytics-top-routes",
    ),
    path(
        "api/v1/admin/analytics/routes/filters",
        RouteFilterStatsView.as_view(),
        name="routes-analytics-filters",
    ),
    path(
        "api/v1/admin/analytics/routes/unresolved",
        RouteUnresolvedStatsView.as_view(),
        name="routes-analytics-unresolved",
    ),
    path(
        "api/v1/admin/analytics/routes/query",
        RouteAnalyticsQueryView.as_view(),
        name="routes-analytics-query",
    ),
    path(
        "api/v1/admin/users/<int:user_id>",
        AdminUserDetailView.as_view(),
        name="admin-user-detail",
    ),
    path(
        "api/v1/admin/analytics/users/overview",
        UserAnalyticsOverviewView.as_view(),
        name="user-analytics-overview",
    ),
    path(
        "api/v1/admin/analytics/feedback",
        FeedbackAnalyticsView.as_view(),
        name="feedback-analytics",
    ),
    path(
        "api/v1/admin/analytics/feedback/summary",
        FeedbackSummaryView.as_view(),
        name="feedback-analytics-summary",
    ),
    path("api/v1/route", RouteOrchestratorView.as_view(), name="route-orchestrator"),
    path("api/v1/route/history", RouteHistoryView.as_view(), name="route-history"),
    path("api/v1/routes/search", RouteSearchView.as_view(), name="route-search"),
    path(
        "api/v1/routes/search/confirm",
        RouteSearchConfirmView.as_view(),
        name="route-search-confirm",
    ),
    path("api/v1/routes/metadata", RouteMetadataView.as_view(), name="route-metadata"),
    path(
        "api/v1/routes/alternatives",
        RouteAlternativesView.as_view(),
        name="route-alternatives",
    ),
    path(
        "api/v1/routes/feedback",
        RouteFeedbackView.as_view(),
        name="route-feedback",
    ),
    path("api/v1/stops/nearby", NearbyStopsView.as_view(), name="stops-nearby"),
    path("api/v1/stops/<str:stop_id>", StopDetailView.as_view(), name="stop-detail"),
    path("api/v1/lines", LinesView.as_view(), name="lines"),
    path("api/v1/lines/<str:route_id>", LineDetailView.as_view(), name="line-detail"),
    path(
        "api/v1/user/saved-locations",
        SavedLocationsView.as_view(),
        name="saved-locations",
    ),
    path(
        "api/v1/user/saved-locations/<int:pk>",
        SavedLocationDetailView.as_view(),
        name="saved-location-detail",
    ),
    path(
        "api/v1/user/favorites",
        FavoriteRoutesView.as_view(),
        name="favorite-routes",
    ),
    path(
        "api/v1/user/favorites/<int:pk>",
        FavoriteRouteDetailView.as_view(),
        name="favorite-route-detail",
    ),
    path(
        "api/v1/user/preferences",
        UserPreferencesView.as_view(),
        name="user-preferences",
    ),
    path("api/health", HealthView.as_view(), name="health"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]
