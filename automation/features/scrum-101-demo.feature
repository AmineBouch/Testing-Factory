# Source : sous-tâches Gherkin SCRUM-110 à SCRUM-117 (Jira) – story SCRUM-101, Test Plan SCRUM-118.
# Chaque scénario porte le tag de son Test Xray pour remonter les résultats.
@SCRUM-101 @demo
Feature: Demo e-commerce customer journey (SCRUM-101)

  @SCRUM-102
  Scenario: Home page loads with the main navigation
    Given I am on the demo home page
    Then the page title is "Automation Exercise"
    And the header menu shows the links:
      | link           |
      | Home           |
      | Products       |
      | Cart           |
      | Signup / Login |
      | Contact us     |

  @SCRUM-103
  Scenario: Product search returns matching products
    Given I am on the products page
    When I search for "dress"
    Then the "Searched Products" section is displayed
    And at least one product is listed
    And every listed product name contains "dress"

  @SCRUM-104
  Scenario: Product search with no match shows no products
    Given I am on the products page
    When I search for "xyzqwerty123"
    Then the "Searched Products" section is displayed
    And no product is listed

  @SCRUM-105
  Scenario: A product added to the cart is shown with its price and quantity
    Given I am on the products page
    When I add the first product to the cart
    And I open the cart
    Then the cart contains 1 product
    And the product line shows a price and quantity 1

  @SCRUM-106
  Scenario: A product removed from the cart is no longer listed
    Given I am on the products page
    And I add the first product to the cart
    And I open the cart
    When I remove the product from the cart
    Then the message "Cart is empty!" is displayed

  @SCRUM-107
  Scenario: Newsletter subscription with a valid email
    Given I am on the demo home page
    When I subscribe to the newsletter with a unique email
    Then the message "You have been successfully subscribed!" is displayed

  @SCRUM-108
  Scenario: Login with invalid credentials is rejected
    Given I am on the login page
    When I log in with email "inconnu.qa@example.com" and password "WrongPass123"
    Then the message "Your email or password is incorrect!" is displayed

  @SCRUM-109
  Scenario: Create an account then delete it
    Given I am on the login page
    When I sign up as "QA Demo" with a unique email
    And I fill in the account information form with valid fictitious data
    And I submit the account creation form
    Then the message "Account Created!" is displayed
    When I continue
    Then I am logged in as "QA Demo"
    When I delete my account
    Then the message "Account Deleted!" is displayed
