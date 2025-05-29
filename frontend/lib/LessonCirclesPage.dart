// ignore_for_file: file_names

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'StartLesson.dart'; // Assuming StartLesson.dart exists and is correctly implemented

class LessonCirclesPage extends StatefulWidget {
  final String hash;

  LessonCirclesPage({required this.hash});

  @override
  _LessonCirclesPageState createState() => _LessonCirclesPageState();
}

class _LessonCirclesPageState extends State<LessonCirclesPage> {
  List<int> lessonNumbers = [];
  bool isLoading = true;
  bool hasError = false;
  String errorMessage = ""; // To store specific error messages for display

  @override
  void initState() {
    super.initState();
    // Log the hash value received by this page
    print("LessonCirclesPage: Initializing with hash: ${widget.hash}");
    fetchLessonList();
  }

  Future<void> fetchLessonList() async {
    // Reset state before fetching
    setState(() {
      isLoading = true;
      hasError = false;
      errorMessage = "";
    });

    // Construct the URL for the backend endpoint
    final url = Uri.parse('http://10.0.2.2:5000/get_lessons_for_hash?hash=${widget.hash}');
    print("LessonCirclesPage: Attempting to fetch lesson list from URL: $url");

    try {
      final response = await http.get(url);

      // Log the response status code and body for debugging
      print("LessonCirclesPage: Response Status Code: ${response.statusCode}");
      print("LessonCirclesPage: Response Body: ${response.body}");

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        // Check if the 'lessons' key exists and is a list
        if (data.containsKey('lessons') && data['lessons'] is List) {
          setState(() {
            lessonNumbers = List<int>.from(data['lessons']);
            isLoading = false;
            print("LessonCirclesPage: Successfully loaded ${lessonNumbers.length} lessons.");
          });
        } else {
          // Handle unexpected JSON structure
          setState(() {
            hasError = true;
            isLoading = false;
            errorMessage = "Invalid data format from server: 'lessons' key missing or not a list.";
            print("LessonCirclesPage Error: $errorMessage");
          });
        }
      } else {
        // Handle non-200 HTTP responses
        setState(() {
          hasError = true;
          isLoading = false;
          errorMessage = 'Failed to load lesson list. Status: ${response.statusCode}, Body: ${response.body}';
          print("LessonCirclesPage Error: $errorMessage");
        });
      }
    } catch (e) {
      // Handle network errors (e.g., server unreachable, no internet)
      print("LessonCirclesPage Network Error: $e");
      setState(() {
        hasError = true;
        isLoading = false;
        errorMessage = 'Network error or server unreachable: $e';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Lessons for ${widget.hash}')),
      body: isLoading
          ? Center(child: CircularProgressIndicator()) // Corrected: CircularProgressIndicator
          : hasError
              ? Center( // Show error message and retry button
                  child: Padding(
                    padding: const EdgeInsets.all(16.0),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(
                          "Error loading lessons:",
                          style: TextStyle(fontSize: 18, color: Colors.red),
                          textAlign: TextAlign.center,
                        ),
                        SizedBox(height: 10),
                        Text(
                          errorMessage,
                          style: TextStyle(fontSize: 14, color: Colors.redAccent),
                          textAlign: TextAlign.center,
                        ),
                        SizedBox(height: 20),
                        ElevatedButton(
                          onPressed: fetchLessonList, // Retry fetching on button press
                          child: Text("Retry"),
                        ),
                      ],
                    ),
                  ),
                )
              : lessonNumbers.isEmpty
                  ? Center( // Show message if no lessons are found
                      child: Text(
                        "No lessons found for this hash. Please add lessons or check the hash.",
                        style: TextStyle(fontSize: 16, color: Colors.grey[700]),
                        textAlign: TextAlign.center,
                      ),
                    )
                  : Center( // Center the entire Column containing the circles
                      child: Padding(
                        padding: const EdgeInsets.all(16.0),
                        child: Column( // Use Column for vertical arrangement
                          mainAxisAlignment: MainAxisAlignment.center, // Center vertically
                          crossAxisAlignment: CrossAxisAlignment.center, // Center horizontally
                          children: lessonNumbers.map((lessonNumber) {
                            return Padding(
                              padding: const EdgeInsets.symmetric(vertical: 8.0), // Add vertical spacing between circles
                              child: GestureDetector(
                                onTap: () {
                                  // Navigate to StartLesson page when a circle is tapped
                                  Navigator.push(
                                    context,
                                    MaterialPageRoute(
                                      builder: (context) => StartLesson(
                                        lessonNumber: lessonNumber,
                                        hash: widget.hash,
                                      ),
                                    ),
                                  );
                                },
                                child: CircleAvatar(
                                  radius: 30, // Size of the circle
                                  backgroundColor: Colors.deepOrangeAccent, // Circle background color
                                  child: Text(
                                    '${lessonNumber + 1}', // Display 1-based lesson number (e.g., 1 instead of 0)
                                    style: TextStyle(
                                        color: Colors.white,
                                        fontSize: 18,
                                        fontWeight: FontWeight.bold),
                                  ),
                                ),
                              ),
                            );
                          }).toList(), // Convert the map result to a list of widgets
                        ),
                      ),
                    ),
    );
  }
}