# Démo d'automatisation sur https://www.saucedemo.com (site public de démonstration de Sauce Labs).
# Sert à illustrer l'exécution Playwright dans la vidéo de présentation (cv/make_cv_video.py).
# Les comptes utilisés sont les comptes de démo publics affichés sur la page de connexion du site.
@saucedemo
Feature: Swag Labs shopping journey (saucedemo.com)

  @SD-1
  Scenario: A standard user logs in and sees the product catalogue
    Given I open the Swag Labs login page
    When I log in to Swag Labs as "standard_user"
    Then the Swag Labs "Products" page is displayed
    And 6 products are listed in the catalogue

  @SD-2
  Scenario: A locked-out user is refused with a clear message
    Given I open the Swag Labs login page
    When I log in to Swag Labs as "locked_out_user"
    Then the Swag Labs login error says "Sorry, this user has been locked out."

  @SD-3
  Scenario: Products sorted by price, two added to the cart
    Given I am logged in to Swag Labs as "standard_user"
    When I sort the products by "Price (low to high)"
    And I add "Sauce Labs Onesie" to the cart
    And I add "Sauce Labs Bike Light" to the cart
    Then the cart badge shows 2
    When I open the Swag Labs cart
    Then the cart lists "Sauce Labs Onesie" and "Sauce Labs Bike Light"

  @SD-4
  Scenario: A full checkout ends with the order confirmation
    Given I am logged in to Swag Labs as "standard_user"
    When I add "Sauce Labs Backpack" to the cart
    And I open the Swag Labs cart
    And I check out as "Test" "QA" with postal code "75001"
    Then the order overview shows the total
    When I finish the order
    Then the Swag Labs confirmation "Thank you for your order!" is displayed
