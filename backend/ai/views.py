from rest_framework.response import Response

from tenancy.api import OrganizationScopedAPIView

from .budget import budget_status


class AIBudgetView(OrganizationScopedAPIView):
    def get(self, request, **kwargs):
        return Response(budget_status(request.organization))
