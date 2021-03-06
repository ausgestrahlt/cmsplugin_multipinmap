from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.template.loader import render_to_string
from django.core.exceptions import ValidationError
from django.conf import settings

from cms.models import CMSPlugin

from geopy.geocoders import Here


def get_geolocation(street: str, postal_code: str, city: str) -> dict:
    geolocator = Here(apikey=settings.HERE_API_KEY)
    location = geolocator.geocode(" ".join([street, postal_code, city]))
    if location:
        return {"lat": location.latitude, "lng": location.longitude}
    return {"lat": None, "lng": None}


class Map(CMSPlugin):

    STYLE_CHOICES = (("google", "Google Maps"), ("leaflet", "Leaflet"))
    style = models.CharField(
        _("style"), max_length=25, choices=STYLE_CHOICES, default="leaflet"
    )

    leaflet_tile_url = models.CharField(
        _("tile url"),
        max_length=255,
        default="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    )

    height = models.IntegerField(
        _("height"), help_text=_("height of the map in px."), default=400
    )
    ZOOM_LEVELS = map(lambda c: (c, str(c)), range(22))
    zoom = models.IntegerField(_("zoom"), choices=ZOOM_LEVELS, default=8)

    # center address
    street = models.CharField(
        _("street"),
        max_length=100,
        help_text=_("address for center of map"),
        null=True,
        blank=True,
    )
    postal_code = models.CharField(_("postal code"), max_length=10)
    city = models.CharField(_("city"), max_length=100)
    lat = models.DecimalField(
        _("lat"), null=True, blank=True, decimal_places=6, max_digits=10
    )
    lng = models.DecimalField(
        _("lng"), null=True, blank=True, decimal_places=6, max_digits=10
    )

    def clean(self, *args, **kwargs):
        if self.style == "mapbox" and self.mapbox_access_token == "":
            raise ValidationError(
                {"mapbox_access_token": _("mapbox access token is required")}
            )
        if self.style == "mapbox" and self.mapbox_map_id == "":
            raise ValidationError({"mapbox_map_id": _("mapbox map id is required")})

        try:
            location = get_geolocation(self.street or "", self.postal_code, self.city)
            self.lat = location["lat"]
            self.lng = location["lng"]
        except:
            raise ValidationError(
                {
                    "street": _("not a valid address"),
                    "postal_code": _("not a valid address"),
                    "city": _("not a valid address"),
                }
            )

    def copy_relations(self, oldinstance):
        for pin in oldinstance.pins.all():
            pin.pk = None
            pin.map_plugin = self
            pin.save()


class Pin(models.Model):
    name = models.CharField(_("name"), max_length=50)
    map_plugin = models.ForeignKey(Map, related_name="pins", on_delete=models.CASCADE)

    street = models.CharField(_("street"), max_length=100, null=True, blank=True)
    postal_code = models.CharField(_("postal code"), max_length=10)
    city = models.CharField(_("city"), max_length=100)

    link = models.URLField(_("link"), blank=True, null=True)
    link_title = models.CharField(
        _("link title"), max_length=255, blank=True, null=True
    )

    description = models.TextField(_("description"), blank=True, null=True)

    COLOR_CHOICES = (
        ("redIcon", _("red")),
        ("blueIcon", _("blue")),
        ("greenIcon", _("green")),
        ("yellowIcon", _("yellow")),
    )

    pin_color = models.CharField(max_length=20, choices=COLOR_CHOICES)

    lat = models.DecimalField(
        _("lat"), null=True, blank=True, decimal_places=6, max_digits=10
    )
    lng = models.DecimalField(
        _("lng"), null=True, blank=True, decimal_places=6, max_digits=10
    )

    @property
    def infowindow(self):
        context = {}
        context["name"] = self.name
        context["street"] = self.street
        context["postal_code"] = self.postal_code
        context["city"] = self.city
        context["link"] = self.link
        context["link_title"] = self.link_title
        context["description"] = self.description

        return render_to_string(
            "cmsplugin_multipinmap/infowindow.html", context
        ).replace("\n", "")

    def clean(self, *args, **kwargs):
        try:
            location = get_geolocation(self.street or "", self.postal_code, self.city)
            self.lat = location["lat"]
            self.lng = location["lng"]
        except:
            raise ValidationError(
                {
                    "street": _("not a valid address"),
                    "postal_code": _("not a valid address"),
                    "city": _("not a valid address"),
                }
            )

    def __str__(self):
        return self.name
