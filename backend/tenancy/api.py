"""Tenant scoping for the API.

Every tenant endpoint lives under /api/o/<org_slug>/. The organization comes from
the URL, so users who belong to several organizations (brokers, consultants,
Nettle staff) can open them side by side and links are explicit.
"""
from rest_framework import serializers, viewsets
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import SAFE_METHODS, IsAuthenticated

from .db import activate_tenant
from .models import Membership


class OrganizationScopedViewSet(viewsets.ModelViewSet):
    """Base class for every tenant endpoint.

    1. The organization is taken from the URL.
    2. The user must be a member; otherwise 404, so other tenants' existence isn't revealed.
    3. Writes require one of `write_roles` (viewers are read-only).
    4. Every query is filtered to the organization; every create is stamped with it.
    5. The request's transaction is scoped to the organization in Postgres too
       (row-level security), so a forgotten filter still can't leak rows.
    """

    permission_classes = [IsAuthenticated]
    write_roles = {Membership.ADMIN, Membership.ENGINEER}

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)  # authentication, IsAuthenticated, throttles
        membership = (
            Membership.objects.select_related("organization")
            .filter(user=request.user, organization__slug=kwargs.get("org_slug"))
            .first()
        )
        if membership is None:
            raise NotFound("Organization not found.")
        if request.method not in SAFE_METHODS and membership.role not in self.write_roles:
            raise PermissionDenied("Your role in this organization is read-only.")
        request.organization = membership.organization
        request.membership = membership
        activate_tenant(membership.organization)

    def get_queryset(self):
        return super().get_queryset().filter(organization=self.request.organization)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["organization"] = getattr(self.request, "organization", None)
        return context

    def perform_create(self, serializer):
        serializer.save(organization=self.request.organization)


def _is_tenant_model(model):
    return any(field.name == "organization" for field in model._meta.fields)


class OrganizationScopedSerializer(serializers.ModelSerializer):
    """Related-object fields only accept objects of the request's organization.

    Another tenant's id is reported as "does not exist", exactly like a random id.
    Without an organization in the context the fields accept nothing (fail closed).
    """

    def get_fields(self):
        fields = super().get_fields()
        organization = self.context.get("organization")
        for field in fields.values():
            relation = getattr(field, "child_relation", field)
            queryset = getattr(relation, "queryset", None)
            if queryset is None or not _is_tenant_model(queryset.model):
                continue
            relation.queryset = (
                queryset.filter(organization=organization) if organization else queryset.none()
            )
        return fields
