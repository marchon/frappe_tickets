# -*- coding: utf-8 -*-
# Copyright (c) 2015, Dirk Chang and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
from frappe.model.document import Document
from frappe import throw, _
from frappe.utils.data import format_datetime
from tickets.tickets.doctype.tickets_site.tickets_site import list_admin_sites


class TicketsTask(Document):
	def validate(self):
		if self.site_type == 'Cell Station':
			self.site_name = frappe.get_value(self.site_type, self.site, "station_name")
		if self.site_type == 'Cloud Project Site':
			self.site_name = frappe.get_value(self.site_type, self.site, "site_name")

	def has_website_permission(self, ptype, verbose=False):
		user = frappe.session.user
		if self.fixed_by == user:
			return True

		teams = [d[0] for d in frappe.db.get_values('Tickets SiteTeam', {"parent": self.site}, "team")]

		for team in teams:
			if frappe.get_value('Tickets TeamUser', {"parent": team, "user": user}):
				return True

		return False

	def wechat_tmsg_data(self):
		remark = _("Site: {0}").format(self.site) + "\n" + \
				_("Prioirty: {0}").format(self.total_cost) + "\n" + \
				_("Info: {0}").format(self.task_desc)
		return {
			"first": {
				"value": _("New Task Created"),
				"color": "red"
			},
			"keyword1": {
				"value": self.name,  # 编号
				"color": "blue"
			},
			"keyword2": {
				"value": self.task_name,  # 标题
				"color": "blue"
			},
			"keyword3": {
				"value": format_datetime(self.modified),  # 时间
				"color": "green",
			},
			"remark": {
				"value": remark
			}
		}

	def wechat_tmsg_url(self):
		return "/update-tickets-task?name=" + self.name

	def update_cost(self):
		tickets = self.get("tickets")
		self.total_cost = 0
		for ticket in tickets:
			self.total_cost += frappe.get_value("Tickets Ticket", ticket.ticket, "cost")
		self.save()

	def append_tickets(self, *tickets):
		if self.docstatus != 1:
			throw(_("Cannot append tickets on un-submitted task"))
			
		current_tickets = [d.ticket for d in self.get("tickets")]
		for ticket in tickets:
			if ticket.name in current_tickets:
				continue
			self.append("tickets", {"ticket": ticket.name})

		self.update_cost()

	def remove_tickets(self, *tickets):
		if self.docstatus != 1:
			throw(_("Cannot append tickets on un-submitted task"))

		existing_tickets = dict((d.ticket, d) for d in self.get("tickets"))
		for ticket in tickets:
			if ticket.name in existing_tickets:
				self.get("tickets").remove(existing_tickets[ticket.name])

		self.update_cost()


def get_task_list(doctype, txt, filters, limit_start, limit_page_length=20, order_by="modified desc"):
	from cloud.cloud.doctype.cloud_company_group.cloud_company import list_user_groups
	groups = [d.name for d in list_user_groups(frappe.session.user)]
	user_groups='"' + '", "'.join(groups) + '"'
	return frappe.db.sql('''select distinct task.*
		from `tabTickets Task` task, `tabTickets SiteTeam` site_team
		where task.docstatus != 2
			and task.site = site_team.parent
			and site_team.team in %(groups)s)
			order by task.{0}
			limit {1}, {2}
		'''.format(order_by, limit_start, limit_page_length),
			{'groups':user_groups},
			as_dict=True,
			update={'doctype':'Tickets Task'})


def get_list_context(context=None):
	return {
		"show_sidebar": True,
		"show_search": True,
		"no_breadcrumbs": True,
		"title": _("Tickets Tasks"),
		"get_list": get_task_list,
		"row_template": "templates/generators/tickets_task_row.html",
	}


def get_permission_query_conditions(user):
	if 'Tickets Manager' in frappe.get_roles(user):
		return ""

	sites = list_admin_sites(user)

	if len(sites) != 0:
		return """(`tabTickets Task`.owner = "{user}" or `tabTickets Task`.site in ({sites}))""".format(
			user = user,
			sites='"' + '", "'.join(sites) + '"')

	return """(`tabTickets Task`.owner = '{0}')""".format(user)


@frappe.whitelist()
def list_task_map():
	sites = list_admin_sites(frappe.session.user)
	if len(sites) == 0:
		return []
	tasks = frappe.get_all('Tickets Task', filters={"docstatus": ["in",[1, 2]], "site": ["in", sites]},
							fields=["name", "task_name", "site", "priority", "total_cost", "status"])

	for task in tasks:
		task.longitude = frappe.get_value('Tickets Site', task.site, "longitude") or '116.3252'
		task.latitude = frappe.get_value('Tickets Site', task.site, "latitude") or '40.045103'
	return tasks
