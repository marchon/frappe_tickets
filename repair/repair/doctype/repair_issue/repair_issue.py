# -*- coding: utf-8 -*-
# Copyright (c) 2015, Dirk Chang and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _


class RepairIssue(Document):

	def has_website_permission(self, ptype, verbose=False):
		user = frappe.session.user
		print('has_website_permission', self.name, user)
		if self.fixed_by == user:
			return True

		teams = [d[0] for d in frappe.db.get_values('Repair SiteTeam', {"parent": self.site}, "team")]

		for team in teams:
			if frappe.get_value('Repair TeamUser', {"parent": team, "user": user}):
				return True

		return False


def get_issue_list(doctype, txt, filters, limit_start, limit_page_length=20, order_by="modified desc"):
	return frappe.db.sql('''select distinct issue.*
		from `tabRepair Issue` issue, `tabRepair TeamUser` team_user, `tabRepair SiteTeam` site_team
		where (issue.site = site_team.parent
			and site_team.team = team_user.parent 
			and team_user.user = %(user)s)
			order by issue.{0}
			limit {1}, {2}
		'''.format(order_by, limit_start, limit_page_length),
			{'user':frappe.session.user},
			as_dict=True,
			update={'doctype':'Repair Issue'})


def get_list_context(context=None):
	return {
		"show_sidebar": True,
		"show_search": True,
		"no_breadcrumbs": True,
		"title": _("Repair Issues"),
		"get_list": get_issue_list,
		"row_template": "templates/generators/repair_issue_row.html",
	}


def list_user_sites(user=None):
	if not user:
		user = frappe.session.user

	teams = [d[0] for d in frappe.db.get_values('Repair TeamUser', {"user": user}, "parent")]
	sites = []
	for team in teams:
		sites.append(d[0] for d in frappe.db.get_values('Repair SiteTeam', {'team': team}, "parent"))

	return sites


def get_permission_query_conditions(user):
	print('get_permission_query_conditions')
	if 'Repair Manager' in frappe.get_roles(user):
		return ""

	else:
		print("""(`tabRepair Issue`.site in ({user_sites}))""".format(
			user_sites='"' + '", "'.join(list_user_sites(user)) + '"'))
		return """(`tabRepair Issue`.site in ({user_sites}))""".format(
			user_sites='"' + '", "'.join(list_user_sites(user)) + '"')


def has_permission(doc, user):
	if 'Repair Manager' in frappe.get_roles(user):
		return True

	if doc.fixed_by == user:
		return True

	teams = [d[0] for d in frappe.db.get_values('Repair SiteTeam', {"parent": doc.site}, "team")]

	for team in teams:
		if frappe.get_value('Repair TeamUser', {"parent": team, "user": user}):
			return True

	return False
