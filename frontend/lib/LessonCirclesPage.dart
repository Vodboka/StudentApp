// ignore_for_file: file_names

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'StartLesson.dart';

class LessonService {
  static const String baseUrl = 'http://10.0.2.2:5000';

  Future<List<Map<String, dynamic>>?> fetchQuestions(String hash, int lessonNumber) async {
    final uri = Uri.parse('$baseUrl/get_lesson_questions')
        .replace(queryParameters: {
      'hash': hash,
      'lesson_number': lessonNumber.toString(),
    });

    try {
      final response = await http.get(uri);

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final questions = data['questions'];

        if (questions is List) {
          return questions
              .map<Map<String, dynamic>>((item) => Map<String, dynamic>.from(item))
              .toList();
        } else {
          print('Unexpected response format for questions for lesson $lessonNumber: ${data}');
          return null;
        }
      } else {
        print('Error fetching lesson questions for lesson $lessonNumber: Status ${response.statusCode}, Body: ${response.body}');
        return null;
      }
    } catch (e) {
      print('Network error fetching lesson questions for lesson $lessonNumber: $e');
      return null;
    }
  }
}

class LessonCirclesPage extends StatefulWidget {
  final String hash;

  LessonCirclesPage({required this.hash});

  @override
  _LessonCirclesPageState createState() => _LessonCirclesPageState();
}

class _LessonCirclesPageState extends State<LessonCirclesPage> {
  List<int> lessonNumbers = [];
  Map<int, double> _lessonPercentages = {}; 
  bool isLoading = true;
  bool hasError = false;
  String errorMessage = "";

  @override
  void initState() {
    super.initState();
    print("LessonCirclesPage: Initializing with hash: ${widget.hash}");
    fetchLessonList();
  }

  // This method will be called when the page comes back into view
  @override
  void didChangeDependencies() {
    super.didChangeDependencies();

    fetchLessonList();
  }


  Future<void> fetchLessonList() async {
    setState(() {
      isLoading = true;
      hasError = false;
      errorMessage = "";
      _lessonPercentages.clear(); // Clear old percentages on new fetch
    });

    final url = Uri.parse('http://10.0.2.2:5000/get_lessons_for_hash?hash=${widget.hash}');
    print("LessonCirclesPage: Attempting to fetch lesson list from URL: $url");

    try {
      final response = await http.get(url);
      print("LessonCirclesPage: Response Status Code: ${response.statusCode}");
      print("LessonCirclesPage: Response Body: ${response.body}");

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        if (data.containsKey('lessons') && data['lessons'] is List) {
          // First, update lessonNumbers
          setState(() {
            lessonNumbers = List<int>.from(data['lessons']);
          });

          // Now, fetch and calculate percentages for each lesson concurrently
          await _fetchAndCalculateAllPercentages();

          setState(() {
            isLoading = false; // Set overall loading to false after all data is ready
          });

        } else {
          setState(() {
            hasError = true;
            isLoading = false;
            errorMessage = "Invalid data format from server: 'lessons' key missing or not a list.";
            print("LessonCirclesPage Error: $errorMessage");
          });
        }
      } else {
        setState(() {
          hasError = true;
          isLoading = false;
          errorMessage = 'Failed to load lesson list. Status: ${response.statusCode}, Body: ${response.body}';
          print("LessonCirclesPage Error: $errorMessage");
        });
      }
    } catch (e) {
      print("LessonCirclesPage Network Error: $e");
      setState(() {
        hasError = true;
        isLoading = false;
        errorMessage = 'Network error or server unreachable: $e';
      });
    }
  }

  // New method to fetch and calculate all percentages for fetched lessons
  Future<void> _fetchAndCalculateAllPercentages() async {
    List<Future<void>> percentageFetchFutures = [];
    final lessonService = LessonService(); // Create one instance for efficiency

    for (int lessonNum in lessonNumbers) {
      percentageFetchFutures.add(_calculateSingleLessonPercentage(lessonService, lessonNum));
    }
    // Wait for all percentage calculations to complete
    await Future.wait(percentageFetchFutures);
  }

  // Helper method to fetch questions and calculate percentage for a single lesson
  Future<void> _calculateSingleLessonPercentage(LessonService lessonService, int lessonNumber) async {
    final questions = await lessonService.fetchQuestions(widget.hash, lessonNumber);

    if (questions != null && questions.isNotEmpty) {
      double sumOfIndividualRates = 0.0;
      int numberOfQuestionsWithAttempts = 0; // Count questions that have at least one attempt

      for (var q in questions) {
        int numberOfTries = (q['number_of_tries'] ?? 0) as int;
        int numberOfCorrectTries = (q['number_of_correct_tries'] ?? 0) as int;

        if (numberOfTries > 0) {
          sumOfIndividualRates += (numberOfCorrectTries / numberOfTries);
          numberOfQuestionsWithAttempts++;
        }

      }

      double averagePercentage = 0.0;
      if (numberOfQuestionsWithAttempts > 0) {
        averagePercentage = (sumOfIndividualRates / numberOfQuestionsWithAttempts) * 100;
      } else if (questions.isNotEmpty) {

        averagePercentage = 0.0;
      }


      _lessonPercentages[lessonNumber] = averagePercentage;
    } else {

      _lessonPercentages[lessonNumber] = 0.0;
    }
  }


  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Lessons for ${widget.hash}')),
      body: isLoading
          ? Center(child: CircularProgressIndicator())
          : hasError
              ? Center(
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
                          onPressed: fetchLessonList,
                          child: Text("Retry"),
                        ),
                      ],
                    ),
                  ),
                )
              : lessonNumbers.isEmpty
                  ? Center(
                      child: Text(
                        "No lessons found for this hash. Please add lessons or check the hash.",
                        style: TextStyle(fontSize: 16, color: Colors.grey[700]),
                        textAlign: TextAlign.center,
                      ),
                    )
                  : Center(
                      child: Padding(
                        padding: const EdgeInsets.all(16.0),
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          crossAxisAlignment: CrossAxisAlignment.center,
                          children: lessonNumbers.map((lessonNumber) {
                            // Retrieve the percentage for the current lesson
                            final percentage = _lessonPercentages[lessonNumber];

                            return Padding(
                              padding: const EdgeInsets.symmetric(vertical: 8.0),
                              child: Row( // Use Row to place circle and percentage side-by-side
                                mainAxisAlignment: MainAxisAlignment.center, // Center the row within the Column
                                children: [
                                  GestureDetector(
                                    onTap: () {
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
                                      radius: 30,
                                      backgroundColor: Colors.deepOrangeAccent,
                                      child: Text(
                                        '${lessonNumber + 1}',
                                        style: TextStyle(
                                            color: Colors.white,
                                            fontSize: 18,
                                            fontWeight: FontWeight.bold),
                                      ),
                                    ),
                                  ),
                                  SizedBox(width: 10), // Space between circle and percentage
                                  // Display the percentage or a loading indicator
                                  if (percentage != null)
                                    Text(
                                      '${percentage.toStringAsFixed(0)}%', // Format as integer percentage
                                      style: TextStyle(
                                          fontSize: 18,
                                          fontWeight: FontWeight.bold,
                                          color: Colors.deepOrange),
                                    )
                                  else
                                    SizedBox( // Show a small sized box with loader while percentage is calculated
                                      width: 20, // Adjust size as needed for the loader
                                      height: 20,
                                      child: CircularProgressIndicator(
                                        strokeWidth: 2,
                                        valueColor: AlwaysStoppedAnimation<Color>(Colors.deepOrange),
                                      ),
                                    ),
                                ],
                              ),
                            );
                          }).toList(),
                        ),
                      ),
                    ),
    );
  }
}
